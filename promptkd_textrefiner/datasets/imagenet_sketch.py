import os

from dassl.data.datasets import DATASET_REGISTRY, Datum, DatasetBase
from dassl.utils import listdir_nohidden
from dassl.utils import mkdir_if_missing
from .imagenet import ImageNet
from .oxford_pets import OxfordPets
import pickle

@DATASET_REGISTRY.register()
class ImageNetSketch(DatasetBase):
    """ImageNet-Sketch.

    This dataset is used for testing only.
    """

    dataset_dir = "imagenet-sketch"

    def __init__(self, cfg):
        root = os.path.abspath(os.path.expanduser(cfg.DATASET.ROOT))
        self.dataset_dir = os.path.join(root, self.dataset_dir)
        self.image_dir = os.path.join(self.dataset_dir, "images")

        # text_file = os.path.join(self.dataset_dir, "classnames.txt")
        # classnames = ImageNet.read_classnames(text_file)
        self.preprocessed = os.path.join(self.dataset_dir, "preprocessed.pkl")
        self.split_fewshot_dir = os.path.join(self.dataset_dir, "split_fewshot")
        mkdir_if_missing(self.split_fewshot_dir)

        if os.path.exists(self.preprocessed):
            with open(self.preprocessed, "rb") as f:
                preprocessed = pickle.load(f)
                train = preprocessed["train"]
                test = preprocessed["test"]
        else:
            text_file = os.path.join(self.dataset_dir, "classnames.txt")
            classnames = ImageNet.read_classnames(text_file)
            train = self.read_data(classnames)
            test = self.read_data(classnames)
        
        preprocessed = {"train": train, "test": test}
        with open(self.preprocessed, "wb") as f:
            pickle.dump(preprocessed, f, protocol=pickle.HIGHEST_PROTOCOL)
            
        num_shots = cfg.DATASET.NUM_SHOTS
        print(f"num_shots is {num_shots}")
        if num_shots >= 1:
            seed = cfg.SEED
            preprocessed = os.path.join(self.split_fewshot_dir, f"shot_{num_shots}-seed_{seed}.pkl")
            
            if os.path.exists(preprocessed):
                print(f"Loading preprocessed few-shot data from {preprocessed}")
                with open(preprocessed, "rb") as file:
                    data = pickle.load(file)
                    train = data["train"]
            else:
                train = self.generate_fewshot_dataset(train, num_shots=num_shots)
                data = {"train": train}
                print(f"Saving preprocessed few-shot data to {preprocessed}")
                with open(preprocessed, "wb") as file:
                    pickle.dump(data, file, protocol=pickle.HIGHEST_PROTOCOL)
       
        subsample = cfg.DATASET.SUBSAMPLE_CLASSES
        if cfg.TRAINER.NAME == "PromptKD":
            if cfg.TRAINER.MODAL == "base2novel":
                train_x, _ = OxfordPets.subsample_classes(train, test, subsample='all')
                _, base_test = OxfordPets.subsample_classes(train, test, subsample='base')
                _, novel_test = OxfordPets.subsample_classes(train, test, subsample='new')
                super().__init__(train_x=train_x, val=base_test, test=novel_test)
            elif cfg.TRAINER.MODAL == "cross":
                train, test = OxfordPets.subsample_classes(train, test, subsample=subsample)
                super().__init__(train_x=train, val=test, test=test)
        else:
            print("normal sample")
            print(f"subsample category: {subsample}")
            train, test = OxfordPets.subsample_classes(train, test, subsample=subsample)
            super().__init__(train_x=train, val=test, test=test) 
        # super().__init__(train_x=data, test=data)

    def read_data(self, classnames):
        image_dir = self.image_dir
        folders = listdir_nohidden(image_dir, sort=True)
        items = []

        for label, folder in enumerate(folders):
            imnames = listdir_nohidden(os.path.join(image_dir, folder))
            classname = classnames[folder]
            for imname in imnames:
                impath = os.path.join(image_dir, folder, imname)
                item = Datum(impath=impath, label=label, classname=classname)
                items.append(item)

        return items
