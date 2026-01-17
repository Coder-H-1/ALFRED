import torch
import os
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification


"""

To use custom intent model  

from intent_classifier import IntentClassifier

clf = IntentClassifier("alfred_intent_model")

result = clf.predict("turn on the kitchen light")
print(result)

"""

class IntentClassifier:
    """
    BERT-based intent classifier (inference only)
    """

    def __init__(self, model_path: str, device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.to(self.device)
        self.model.eval()

        self.id2label = self.model.config.id2label

    @torch.no_grad()
    def predict(self, text: str) -> dict:
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True
        ).to(self.device)

        outputs = self.model(**inputs)
        logits = outputs.logits.squeeze(0)

        probs = F.softmax(logits, dim=-1)
        idx = torch.argmax(probs).item()

        return {
            "intent": self.id2label[idx],
            "confidence": round(probs[idx].item(), 4)
        }


import json
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments
)

#############################################################################################################################################################
### INTENT MODEL TRAINER
#############################################################################################################################################################


class IntentDataset(Dataset):
    def __init__(self, path, tokenizer, label2id, max_len=128):
        self.samples = []
        self.tokenizer = tokenizer
        self.label2id = label2id
        self.max_len = max_len

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                self.samples.append(obj)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        item = self.samples[idx]

        encoding = self.tokenizer(
            item["text"],
            truncation=True,
            padding="max_length",
            max_length=self.max_len
        )

        return {
            "input_ids": torch.tensor(encoding["input_ids"]),
            "attention_mask": torch.tensor(encoding["attention_mask"]),
            "labels": torch.tensor(self.label2id[item["intent"]])
        }

"""
To use Trainer, use

from intent_trainer import IntentTrainer

trainer = IntentTrainer(
    base_model="distilbert-base-uncased",
    output_dir="alfred_intent_model"
)

trainer.train(
    train_file="intent_dataset.jsonl",
    epochs=5,
    batch_size=16
)

"""

class IntentTrainer:
    """
    Fine-tunes a BERT-style model for intent classification
    """

    def __init__(
        self,
        base_model: str = "distilbert-base-uncased",
        output_dir: str = "intent_model"
    ):
        self.base_model = base_model
        self.output_dir = output_dir

    def train(
        self,
        train_file: str,
        epochs: int = 5,
        batch_size: int = 16,
        lr: float = 2e-5
    ) -> str:
        tokenizer = AutoTokenizer.from_pretrained(self.base_model)

        # Load dataset once to extract labels
        intents = set()
        with open(train_file, "r", encoding="utf-8") as f:
            for line in f:
                intents.add(json.loads(line)["intent"])

        intents = sorted(intents)
        label2id = {label: i for i, label in enumerate(intents)}
        id2label = {i: label for label, i in label2id.items()}

        model = AutoModelForSequenceClassification.from_pretrained(
            self.base_model,
            num_labels=len(intents),
            label2id=label2id,
            id2label=id2label
        )

        dataset = IntentDataset(train_file, tokenizer, label2id)

        args = TrainingArguments(
            output_dir=self.output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            learning_rate=lr,
            logging_steps=50,
            save_strategy="epoch",
            report_to="none"
        )

        trainer = Trainer(
            model=model,
            args=args,
            train_dataset=dataset,
            tokenizer=tokenizer
        )

        trainer.train()

        trainer.save_model(self.output_dir)
        tokenizer.save_pretrained(self.output_dir)

        return "Trained the intention model, Will need a quick restart for myself to implement changes."


class INTENT:
    def __init__(self, model:str = None) -> None:
        self.classifier:object = IntentClassifier("intent_model" if model==None else model)
        self.train_file = "FILES/model/data/intents.jsonl"
        self.base_model = "distilbert-base-uncased"
        self.output_dir = "FILES/model/intent_model"

    def get(self, text: str) -> tuple:
        if self.__check_intent_model__():
            prediction:tuple = self.classifier.predict(text) # returns (intent:str, confidence:int)
            return (prediction['intent'], prediction['confidence']) if prediction['confidence'] >= 0.6 else ("UNKNONN" , 0)
    
    def __check_intent_model__(self) -> bool: return os.path.exists(self.output_dir)
    def __check_train_file__(self) -> bool: return os.path.exists(self.train_file)

    def Start_trainer(self) -> bool:
        try:
            if self.__check_train_file__():
                trainer = IntentTrainer(
                    base_model= self.base_model,
                    output_dir= self.output_dir
                )

                trainer.train(
                    train_file=self.train_file,
                    epochs=4, batch_size=8
                )
                return True

            else: return False

        except Exception as Error:
            print(Error)
            return False 




### This method is still not completed. Will not work as intented.