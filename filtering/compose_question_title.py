import time, os, sys, subprocess
import langextract as lx
import textwrap
from database import db_client

num_questions = None
session = db_client.client.start_session()
questions_collection = db_client.get_collection("Questions")

# Get question documents
if num_questions is None:
    print("Fetching ALL questions from the database...")
    question_docs = questions_collection.find(no_cursor_timeout=True, session=session)
else:
    print(f"Fetching {num_questions} questions from the database...")
    question_docs = questions_collection.find().limit(num_questions)


# 1. Define the prompt and extraction rules
prompt = textwrap.dedent("""\
    Extract exactly one high-quality title and exactly one teaching point from the provided medical question text—the single best ones that represent the core focus. The title should be a concise internal title or topic summarizing the question's main theme, inferred from the content if not explicitly stated. The teaching point should capture the primary learning objective or core lesson being conveyed, synthesized concisely from the question, options, and especially the explanation—focusing on the specific physiological, pathological, clinical, or therapeutic insight the student should learn (e.g., the mechanism, diagnosis criterion, treatment rationale, or key distinction). Do not simply rephrase the title; make it deeper and more meaningful by summarizing the actual message or takeaway. Do not generate multiples, alternatives, duplicates, or overlaps; select only the most representative pair. Do not paraphrase unnecessarily; aim for precision, depth, and relevance to medical education. Output in the specified format.
""")

# 2. Provide high-quality examples to guide the model
examples = [
    lx.data.ExampleData(
        text="Question: A 45-year-old man presents with chest pain radiating to the left arm, shortness of breath, and diaphoresis. His ECG shows ST-segment elevation in leads V2-V4. Which of the following is the most likely diagnosis? Options: 1) Stable angina 2) Acute myocardial infarction 3) Pericarditis 4) Aortic dissection Explanation: OPTION 1 is Incorrect. Stable angina typically presents with exertional chest pain relieved by rest. OPTION 2 is Correct. ST-elevation myocardial infarction (STEMI) is characterized by acute chest pain, ECG changes, and requires immediate reperfusion. OPTION 3 is Incorrect. Pericarditis shows diffuse ST elevation. OPTION 4 is Incorrect. Aortic dissection presents with tearing pain. The core concept is recognizing acute coronary syndromes.",
        extractions=[
            lx.data.Extraction(
                extraction_class="title",
                extraction_text="Diagnosis of Acute Chest Pain with ST-Elevation",
                attributes={}
            ),
            lx.data.Extraction(
                extraction_class="teaching_point",
                extraction_text="ST-segment elevation in anterior leads (V2-V4) with radiating chest pain and diaphoresis indicates STEMI, requiring immediate reperfusion therapy",
                attributes={}
            ),
        ]
    ),
    lx.data.ExampleData(
        text="Question: A 30-year-old woman has recurrent urinary tract infections. Urinalysis shows nitrites and leukocytes. What is the most appropriate next step? Options: 1) Empirical antibiotics 2) Renal ultrasound 3) Cystoscopy 4) IV pyelogram Explanation: OPTION 1 is Correct. For uncomplicated UTI in women, empirical treatment with trimethoprim-sulfamethoxazole is standard. OPTION 2 is Incorrect. Imaging is for complicated cases. OPTION 3 is Incorrect. Reserved for recurrent or atypical cases. OPTION 4 is Incorrect. Not first-line. The key is understanding UTI management.",
        extractions=[
            lx.data.Extraction(
                extraction_class="title",
                extraction_text="Management of Recurrent Urinary Tract Infections in Women",
                attributes={}
            ),
            lx.data.Extraction(
                extraction_class="teaching_point",
                extraction_text="Empirical treatment with trimethoprim-sulfamethoxazole is the standard first-line therapy for uncomplicated UTIs in women, without need for initial imaging",
                attributes={}
            ),
        ]
    ),
    lx.data.ExampleData(
        text="Question: A 52-year-old woman with a history of type 2 diabetes mellitus presents with progressive weakness, numbness in her extremities, and blurred vision. Laboratory studies show elevated HbA1c and microalbuminuria. Nerve conduction studies reveal demyelination. Which of the following is the most likely underlying mechanism? Options: 1) Autoimmune attack on myelin sheath 2) Advanced glycation end-products accumulation 3) Viral demyelination 4) Genetic mutation in myelin protein 5) Toxic exposure Explanation: OPTION 1 is Incorrect. Autoimmune demyelination is seen in multiple sclerosis, not typically associated with diabetes. OPTION 2 is Correct. Diabetic neuropathy involves polyol pathway activation, oxidative stress, and AGEs leading to nerve damage and demyelination. OPTION 3 is Incorrect. Viral causes like progressive multifocal leukoencephalopathy are rare and not linked to diabetes. OPTION 4 is Incorrect. Genetic causes like Charcot-Marie-Tooth disease present earlier. OPTION 5 is Incorrect. No history of toxins. The core concept is complications of chronic hyperglycemia in diabetes.",
        extractions=[
            lx.data.Extraction(
                extraction_class="title",
                extraction_text="Pathophysiology of Diabetic Neuropathy and Demyelination",
                attributes={}
            ),
            lx.data.Extraction(
                extraction_class="teaching_point",
                extraction_text="Advanced glycation end-products accumulation in diabetic neuropathy leads to nerve damage and demyelination via polyol pathway activation and oxidative stress",
                attributes={}
            ),
        ]
    ),
    lx.data.ExampleData(
        text="Question: A 65-year-old man with a 40-pack-year smoking history presents with hemoptysis, weight loss, and a mass on chest X-ray. Biopsy shows squamous cell carcinoma. Molecular testing reveals EGFR mutation. What is the most appropriate targeted therapy? Options: 1) Erlotinib 2) Crizotinib 3) Pembrolizumab 4) Carboplatin plus paclitaxel 5) Bevacizumab Explanation: OPTION 1 is Correct. EGFR tyrosine kinase inhibitors like erlotinib are first-line for EGFR-mutated non-small cell lung cancer. OPTION 2 is Incorrect. Crizotinib targets ALK fusions, not EGFR. OPTION 3 is Incorrect. Pembrolizumab is for PD-L1 high expression. OPTION 4 is Incorrect. Chemotherapy is for non-mutated cases. OPTION 5 is Incorrect. Bevacizumab is anti-angiogenic, avoided in squamous histology due to bleeding risk. The core concept is precision oncology in lung cancer.",
        extractions=[
            lx.data.Extraction(
                extraction_class="title",
                extraction_text="Targeted Therapy for EGFR-Mutated Non-Small Cell Lung Cancer",
                attributes={}
            ),
            lx.data.Extraction(
                extraction_class="teaching_point",
                extraction_text="Erlotinib, an EGFR tyrosine kinase inhibitor, is the first-line targeted therapy for EGFR-mutated non-small cell lung cancer, outperforming chemotherapy in mutated cases",
                attributes={}
            ),
        ]
    ),
]

count = 0

for question_doc in question_docs:
    question_id = question_doc.get("_id")
    if question_doc.get("title"):
        count += 1
        continue
    
    result = None
    input_text = question_doc.get("text")
    try:
        result = lx.extract(
            text_or_documents=input_text,
            prompt_description=prompt,
            examples=examples,
            model_id="gemini-1.5-flash",
        )
    except Exception as e:
        print(f"❌ Failed to extract title for question {question_id}: {e}")
        failed.append(question_id)
        print(f"Number of failed questions: {len(failed)}")
        print(f"Number of successful questions: {count}")
        continue

    if not result:
        continue

    titles = [ext.extraction_text for ext in result.extractions if ext.extraction_class == 'title']
    title = titles[0]
    teaching_points = [ext.extraction_text for ext in result.extractions if ext.extraction_class == 'teaching_point']

    failed = []

    success = db_client.update_document(
        collection_name="Questions",
        document_id=question_id,
        updates={"title": title, "teaching_points": teaching_points}
    )

    if not success:
        failed.append(question_id)
        print(f"❌ Failed to update question {question_id}")
    else:
        count += 1
        print(count)

session.end_session()
