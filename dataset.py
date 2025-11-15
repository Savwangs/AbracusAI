from datasets import load_dataset

splits = ["medical_equipment_outbound", "insurance_outbound"]

datasets = {
    split: load_dataset("AIxBlock/92k-real-world-call-center-scripts-english", split)
    for split in splits
}
