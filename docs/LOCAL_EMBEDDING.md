# Local Embedding — Manual Model Setup

The MPNet embedding model (`all-mpnet-base-v2`) must be downloaded manually and placed in the
backend service folder. This is required because HuggingFace downloads fail on the WEX corporate
network due to SSL certificate inspection.

---

## Where the model lives

```
services/backend/models/sentence-transformers/all-mpnet-base-v2/
```

This path matches the `model_path` value stored in the `integrations` table for the
**MPNet base-v2** embedding provider.

---

## Option 1 — Download on a machine outside the WEX network (recommended)

Use a personal laptop, home machine, or any machine without corporate SSL inspection.

### Step 1 — Install the library (if not already installed)

```bash
pip install sentence-transformers
```

### Step 2 — Run the download script

```python
import os
from sentence_transformers import SentenceTransformer

save_path = "models/sentence-transformers/all-mpnet-base-v2"
os.makedirs(os.path.dirname(save_path), exist_ok=True)

print("Downloading model (~420 MB)...")
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
model.save(save_path)
print(f"Saved to: {save_path}")
```

Run this from inside `services/backend/` so the path resolves correctly:

```bash
cd services/backend
python download_model.py
```

### Step 3 — Copy the folder to the target machine

Copy the entire `models/` folder to the same relative location on the target machine:

```
Target: C:\workspace\gus-pulse\services\backend\models\
```

You can use a USB drive, network share, or any file transfer method.

---

## Option 2 — Download via HuggingFace CLI

If you have `huggingface_hub` installed and access to HuggingFace outside the corporate network:

```bash
pip install huggingface_hub

huggingface-cli download sentence-transformers/all-mpnet-base-v2 \
  --local-dir services/backend/models/sentence-transformers/all-mpnet-base-v2
```

---

## Option 3 — Download directly from HuggingFace website

1. Go to: https://huggingface.co/sentence-transformers/all-mpnet-base-v2/tree/main
2. Download these files manually:
   - `config.json`
   - `tokenizer_config.json`
   - `tokenizer.json`
   - `vocab.txt`
   - `special_tokens_map.json`
   - `pytorch_model.bin` *(or `model.safetensors` — download one)*
   - `sentence_bert_config.json`
   - `modules.json`
   - `1_Pooling/config.json`
3. Place them in:
   ```
   services/backend/models/sentence-transformers/all-mpnet-base-v2/
   services/backend/models/sentence-transformers/all-mpnet-base-v2/1_Pooling/
   ```

---

## Verify it works

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("models/sentence-transformers/all-mpnet-base-v2")
test = model.encode(["Hello world"])
print(f"OK — embedding dimensions: {test.shape[1]}")  # should print 768
```

---

## Activate in the UI

Once the folder is in place:

1. Go to **AI Configuration → Embedding Providers**
2. Click **Edit** on **MPNet base-v2**
3. Confirm `model_path` is `models/sentence-transformers/all-mpnet-base-v2`
4. Set **Source** to `local`, **Active** to checked
5. Click **Save Changes**

The embedding worker will load the model from the local folder on the next ETL job.

---

## On another machine (transferring the model)

If you already have the model downloaded on one machine, just copy the folder:

```
FROM: C:\workspace\gus-pulse\services\backend\models\
  TO: C:\workspace\gus-pulse\services\backend\models\   (on the new machine)
```

No internet access required after this copy.
