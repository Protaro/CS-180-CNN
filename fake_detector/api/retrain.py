import sqlite3
import io
import shutil
import torch
import random
from PIL import Image
from torch.utils.data import Dataset
from transformers import (
  ViTImageProcessor,
  ViTForImageClassification,
  TrainingArguments,
  Trainer
)

DB_PATH = "feedback.db"
MODEL_PATH = "Veritas_ViT_Gen2"
LABEL_MAP = {
  "real": 0,
  "fake": 1
}

class SimpleDataset(Dataset):
  def __init__(self, data):
    self.data = data

  def __len__(self):
    return len(self.data)

  def __getitem__(self, idx):
    return self.data[idx]
  
def start_retrain():
  model = ViTForImageClassification.from_pretrained(MODEL_PATH)
  processor = ViTImageProcessor.from_pretrained(MODEL_PATH)

  shutil.copytree(
    MODEL_PATH,
    "Veritas_ViT_backup",
    dirs_exist_ok=True
  )

  for param in model.vit.parameters():
    param.requires_grad = False

  training_args = TrainingArguments(
    output_dir="./temp_train",
    learning_rate=1e-5,
    per_device_train_batch_size=8,
    num_train_epochs=1,
    save_strategy="epoch",
    logging_steps=5,
    remove_unused_columns=False
  )

  conn = sqlite3.connect(DB_PATH)
  cur = conn.cursor()
  cur.execute("""
  SELECT image, accurate, label
  FROM feedback
  """)
  rows = cur.fetchall()
  conn.close()

  data = []
  for img_bytes, accurate, label in rows:
    true_label = label.lower() if accurate else ("real" if label.lower() == "fake" else "fake")

    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    data.append({
      "pixel_values": inputs["pixel_values"].squeeze(),
      "labels": torch.tensor(LABEL_MAP[true_label])
    })
    
  random.shuffle(data)
  train_dataset = SimpleDataset(data)
  trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset
  )

  trainer.train()
  trainer.save_model(MODEL_PATH)
  processor.save_pretrained(MODEL_PATH)

  conn = sqlite3.connect(DB_PATH)
  cur = conn.cursor()
  cur.execute("DELETE FROM feedback")
  cur.execute("DELETE FROM sqlite_sequence WHERE name='feedback'")
  conn.commit()
  conn.close()

  print("Retraining complete!")

if __name__ == '__main__':
  conn = sqlite3.connect("feedback.db")
  cur = conn.cursor()
  cur.execute("SELECT COUNT(*) FROM feedback")
  count = cur.fetchone()[0]
  conn.close()
  
  if count >= 100:
    start_retrain()
  else:
    print("The database needs to have at least 100 entries to retrain the AI model!")
  
  # start_retrain()