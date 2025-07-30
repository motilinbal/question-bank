### Part 1: Elaboration of the Business Problem

The core business problem you've described is the development of a **high-fidelity, domain-specific semantic search engine for a specialized medical knowledge base**. This isn't merely a text search; it's a knowledge discovery and precision-learning tool intended for a sophisticated audience—medical students, residents, physicians, and researchers—who operate in an environment where nuance and accuracy are paramount.

Let's dissect the multifaceted nature of this challenge:

**1. The Corpus Complexity: Beyond Simple Text**
Your data isn't a collection of unstructured documents; it's a structured corpus of didactic material. Each item is a triad:

  * **Question Body:** Typically a clinical vignette or a theoretical query. This section sets the context, presenting symptoms, patient history, lab results, or abstract concepts.
  * **Options:** A set of potential answers, usually one correct and several "distractors." These distractors are not random; they are carefully crafted to represent common misconceptions, closely related differential diagnoses, or plausible but incorrect reasoning paths. They are, in themselves, valuable semantic information about what the question is *not* about.
  * **Explanation:** This is the canonical ground truth. It justifies the correct answer and, critically, often explains why the distractors are incorrect. It provides the core pedagogical payload, connecting the dots between the presented case and the underlying medical principles.

A successful system must understand the distinct role of each component. Simply concatenating them into a single block of text risks diluting the core signal. The model must learn that the explanation carries the highest weight of "truth" and that the distractors represent "anti-patterns" or related-but-distinct concepts.

**2. The Searcher's Intent: Complex Clinical Reasoning**
The end-user is not performing a simple keyword search like "diabetes symptoms." Their queries will reflect a complex, multi-dimensional thought process, for example:

> "Show me questions about a young, otherwise healthy patient presenting with acute-onset polyuria and polydipsia, but with a normal glucose level. I'm interested in cases that differentiate between central and nephrogenic diabetes insipidus, especially those involving lithium use as a potential cause."

This query contains multiple, intertwined concepts: patient demographics (young, healthy), clinical presentation (polyuria, polydipsia), key negative findings (normal glucose), a differential diagnosis (central vs. nephrogenic DI), and a specific etiological factor (lithium). The search system must be able to decompose this query and find questions that match this specific constellation of features, not just questions that happen to contain the word "lithium" or "diabetes."

**3. The Core Challenge: Semantic Granularity and Salience**
This is the crux of the problem you've rightly identified.

  * **Granularity:** The embedding vector must operate at the level of fine-grained medical distinctions. It cannot simply map a question to the broad topic of "Cardiology." It must be able to differentiate between:

      * *Takotsubo cardiomyopathy* vs. *Myocardial infarction with non-obstructive coronary arteries (MINOCA)*.
      * *Crohn's disease* involving the terminal ileum vs. *Ulcerative colitis* with pancolitis.
      * The mechanism of action of a *SGLT2 inhibitor* vs. a *GLP-1 agonist* in managing Type 2 Diabetes.
        General-purpose embedding models, trained on web text, often fail at this level of specificity. They may see "chest pain" and "elevated troponins" and map two very different underlying pathologies to a similar vector space because they lack the specialized training to grasp the subtle, differentiating clinical data points.

  * **Salience:** The model must identify the "pivotal idea" or the central teaching point of the question. A question about managing hypertensive crisis might include a patient's social history in the vignette. The embedding model must learn that the core concept is the pharmacology of IV labetalol vs. hydralazine, and that the social history, while providing context, is not the salient feature for semantic representation. It must not be "distracted" by ancillary information, focusing instead on the central diagnostic or therapeutic challenge being presented.

**4. The Technical Constraint: The Single Vector Representation**
The requirement of a single embedding vector per question is a standard but non-trivial constraint. It forces a compression of all the rich, structured information (vignette, options, explanation) into a fixed-dimensional point in a high-dimensional space. The challenge is to ensure this compression is not "lossy" with respect to the critical semantic information. The vector must become a dense, potent representation of the question's core medical essence.

-----

### Part 2: The Task and Recommended Technologies

**Restated Professional Task:**

Our objective is to engineer a domain-specific semantic representation model for a corpus of structured medical multiple-choice questions. This model must produce a single, high-fidelity embedding vector for each question item (question, options, and explanation). The resulting embeddings must exhibit high granularity, enabling the differentiation of subtle clinical and theoretical concepts, and high salience, focusing on the core pedagogical intent of each question. This system will power a precision information retrieval engine capable of ranking the entire question bank against complex, natural-language clinical queries, ultimately serving as an advanced medical education and knowledge discovery tool.

**Brainstorming Gold-Standard Technologies:**

We will approach this as a phased strategy, moving from a strong baseline to the absolute state-of-the-art.

#### Phase 1: The High-Quality Baseline (Off-the-Shelf)

This phase establishes a benchmark and can be implemented relatively quickly.

  * **Technology:** State-of-the-art sentence transformer models.
  * **Models to Consider:**
      * **OpenAI `text-embedding-3-large`:** A very powerful, general-purpose model. It's a black box, but its performance is top-tier. It's a great starting point to see what a massive, generalist model can do.
      * **Cohere `embed-v3.0`:** Specifically designed for retrieval (`search_document` and `search_query` modes), which is a direct fit for this task. It often shows strong performance on retrieval benchmarks.
      * **Open Source (e.g., via Hugging Face):** Models like `BAAI/bge-large-en-v1.5` or `intfloat/e5-mistral-7b-instruct`. These models are leaders on the MTEB (Massive Text Embedding Benchmark) leaderboard and offer the flexibility of local hosting and fine-tuning.
  * **Implementation Strategy:**
    1.  **Structured Input:** Do not just concatenate the text. Create a structured, descriptive input string for each question. This leverages the in-context learning capabilities of modern models.
        ```
        Title: [Question's internal title or topic, if available]

        Case Presentation: [Paste question body here]

        Options:
        A) [Option A text]
        B) [Option B text]
        C) [Option C text]
        D) [Option D text]

        Correct Answer Explanation: [Paste full explanation here]

        Key Learning Objective: [This is the core concept being tested]
        ```
        This format helps the model differentiate the roles of each text segment.
    2.  **Generate Embeddings:** Pass this structured string through the chosen model to get your single vector.
    3.  **Vector Database:** Store these vectors in a specialized vector database like Pinecone, Weaviate, or ChromaDB for efficient nearest-neighbor search.
  * **Expected Outcome:** This will likely work reasonably well for broad queries but will fail on the "nuance" and "granularity" tests. It will confuse similar-sounding syndromes and may be distracted by non-salient features. This is our baseline to beat.


As it is the first phase to tackle, we would focus on it for the time being. The goal is to fully set the stage and characterize the phase 1 step of our project. We would only focus on it for the time being, since it would take some time anyway. 

-----

### \#\# A Refined Technical Plan for Phase 1

Let's break it down into a concrete, five-step engineering workflow, adding important technical details and slight modifications for efficiency and robustness.

#### **Step 1: Data Extraction and Deterministic Cleaning**

Before involving an LLM, we should perform as much cleaning as possible using deterministic tools. This is faster, cheaper, and more reliable for rule-based tasks.

  * **Action**: Create a Python script using `pymongo` to connect to your MongoDB and iterate through the `Questions` collection.
  * **HTML to Plain Text**: For each document, extract the `question`, `choices[n].text`, and `explanation` HTML fields. Instead of using an LLM for this, use a dedicated HTML parsing library like **`BeautifulSoup`**.
      * **Why?** `BeautifulSoup` is purpose-built for this task. It's extremely fast, free to run, and will handle malformed HTML gracefully. Using a powerful LLM to strip tags is like using a sledgehammer to crack a nut—it's slow, expensive at scale, and non-deterministic.
      * **Implementation**: The command `BeautifulSoup(html_string, "html.parser").get_text()` will effectively strip all tags and return clean text.
  * **Reconstruction**: Ignore the existing `text` field as it's unreliable. After cleaning each component, you will have pristine plain text versions of the question, each choice, and the explanation.

#### **Step 2: Semantic Structuring & Augmentation with an LLM**

This is where your idea to use a powerful LLM like **Gemini 1.5 Pro** is perfectly placed. Its large context window and advanced reasoning are ideal for understanding the entire medical case, not just cleaning it. For each question document (using the clean text from Step 1), the LLM will perform several high-value semantic tasks in a single pass:

  * **Generate a Concise Clinical Title**: The `name` field (`0KaeUl`) is not useful. The LLM can generate a meaningful title. For your example, it might produce: *"Hypovolemic Shock from Hematemesis in a Patient with Chronic Alcohol Use"*.
  * **Distill the Key Learning Objective**: This is arguably the most critical task. The LLM reads the entire case and explanation to determine the core pedagogical point. For the example, it would be: *"To recognize the signs of hypovolemic shock and understand that the resulting decrease in arterial pressure leads to decreased carotid baroreceptor firing activity."*
  * **Create a Hierarchical Tagging System**: Your idea for tagging is excellent. To make it even more powerful for filtering, we should ask the LLM to generate tags within a defined hierarchical taxonomy. You provide the schema, and the LLM populates it.
      * **Example Taxonomy**:
        ```json
        {
          "system": "Cardiovascular System",
          "condition": "Shock",
          "subtype": "Hypovolemic Shock",
          "pathophysiology": "Baroreceptor Reflex"
        }
        ```
    This provides a much richer basis for faceted search than a flat list of tags.

The output from this step should be a clean JSON object for each question, containing these newly generated fields.

#### **Step 3: Assemble the Final Document for Embedding**

Now, combine the outputs of the previous steps into the final, structured text block that will be fed to the embedding model. This uses your proposed format, but is populated with clean, LLM-augmented data.

```
Title: Hypovolemic Shock from Hematemesis in a Patient with Chronic Alcohol Use

Case Presentation: A 52-year-old man is brought to the emergency department for recurrent vomiting... Which of the following is most likely decreased in this patient in response to his hematemesis?

Options:
A) Systemic vascular resistance
B) Capillary fluid absorption
C) Fractional tissue oxygen extraction
D) Carotid baroreceptor firing activity
E) Pulmonary vascular resistance
F) Cardiac inotropy

Correct Answer Explanation: OPTION D is Correct. Baroreceptors are mechanoreceptors that fire in response to blood vessel stretching... In hypotensive states, decreased arterial pressure results in decreased stretching of the arterial wall and decreased carotid (and aortic) baroreceptor firing activity... [Rest of cleaned explanation text]

Key Learning Objective: To recognize the signs of hypovolemic shock and understand that the resulting decrease in arterial pressure leads to decreased carotid baroreceptor firing activity.
```

#### **Step 4: Embedding Generation**

You asked if **`BAAI/bge-large-en-v1.5`** is the best model. For this phase, it is an **excellent and strategically sound choice**.

  * **Why `BGE` is a Great Choice**: It's a top-performing open-source model on retrieval benchmarks (MTEB), striking a great balance between performance and resource requirements. Most importantly, because it's open-source, it provides a **consistent architectural baseline** for the fine-tuning we will perform in Phase 2. This allows us to scientifically measure the uplift from fine-tuning. Starting with a proprietary API would force a model switch later, confounding our results.

  * **Process**: You will use a library like `sentence-transformers` in Python to load the `bge-large` model. You'll then pass the final structured text document from Step 3 to its `encode()` method to get back a 1024-dimension vector. This process will be batched for efficiency across your entire database.

#### **Step 5: Vector Storage and Indexing**

Your choice of **Weaviate** or **Pinecone** is correct. They are both industry-leading vector databases. The crucial step here is to store not only the vector but also key metadata.

  * **Implementation**: For each question, you will load the following into your vector database:

    1.  The **embedding vector** itself.
    2.  A **metadata payload** containing:
          * The original question `_id` from MongoDB (e.g., `'fa06e587-fbeb-4277-9494-156cbcf72bd2'`).
          * The new hierarchical tags generated by the LLM (e.g., `system: 'Cardiovascular'`, `condition: 'Shock'`).
          * Other useful fields for filtering, like `source` or `difficult`.

  * **Why this is critical**: This enables **hybrid search**. Your application can perform a semantic search *and* filter on metadata simultaneously. A user could search for "a patient with sudden chest pain and ST elevation" (semantic) but filter to only show questions where `source = 'uworld3'` and `tag.subtype = 'Myocardial Infarction'` (metadata filtering). The search returns a list of `_id`s, which you then use to fetch the full question details from MongoDB to display to the user.

-----

### \#\# The Goals of Phase 1: A Deep Characterization

This initial phase is far more than just a preliminary step; it is the foundation upon which the entire project's success is built. Its goals are multi-faceted and crucial.

#### **Goal 1: Establish a Functional, End-to-End Production Pipeline ⚙️**

The primary objective is to build and validate the complete "scaffolding" of the application. This means creating a reliable, automated workflow that handles everything from data extraction from MongoDB to the final, queryable API endpoint provided by the vector database. Success here means we have a working system that can ingest a raw medical question and, in a reasonable amount of time, make it discoverable via semantic search. This proves the viability of the core architecture and de-risks all future development.

#### **Goal 2: Transform the Raw Data into a Structured, Enriched Knowledge Corpus 📚**

This phase's most valuable output, aside from the embeddings themselves, is the **creation of a new, clean, and semantically enriched dataset**. We are transforming messy, HTML-laden documents with useless IDs into pristine, structured text with expert-level clinical titles, explicit learning objectives, and a consistent, hierarchical tagging system. This cleaned corpus is a durable asset that can be used for many future applications beyond this specific search project.

#### **Goal 3: Generate a Quantifiable and Qualitative Performance Baseline 📊**

We cannot know if we are improving if we don't know where we started. A critical goal of Phase 1 is to establish a rigorous performance benchmark. Using a "challenge set" of complex medical queries curated by domain experts, we will quantitatively measure the out-of-the-box performance of the `BGE` model using standard information retrieval metrics like **nDCG@10 (Normalized Discounted Cumulative Gain)** and **Recall@k**. This baseline will provide the hard data needed to justify the significant investment in computational resources and effort required for the fine-tuning in Phase 2.

#### **Goal 4: Uncover the Inherent Weaknesses of a Generalist Model 🔬**

A key goal is to intentionally find where the baseline model fails. By analyzing the results from our challenge set, we will precisely identify the types of nuance a general-purpose model cannot grasp. Does it confuse Crohn's disease with ulcerative colitis? Does it fail to differentiate between various types of shock? These failures are not setbacks; they are **invaluable intelligence**. They provide a data-driven roadmap for Phase 2, telling us exactly which concepts need to be forced apart through hard negative mining during fine-tuning. This phase is designed to give us a "map" of the model's confusion, which is essential for teaching it to be an expert.


Incorporating a human-in-the-loop (HITL) feedback mechanism from the very beginning of Phase 1 is a proactive and strategically brilliant move. It essentially turns your initial user base into a distributed team of medical experts who are constantly generating high-quality training data for you. This will create a powerful "data flywheel" that will massively accelerate and improve the fine-tuning efforts in Phase 2.

Let's plan this out properly to ensure the collected data is structured for maximum utility.

-----

### \#\# Feedback Data Storage: The `FeedbackEvents` Collection 🗄️

You are correct; this feedback should absolutely be stored in its own dedicated collection within MongoDB, which we can call **`FeedbackEvents`**. This is best practice for separating transactional application data (the questions) from interaction/event data (the feedback).

For each feedback click (either "Relevant" or "Not Relevant"), we should log a single document with a rich, contextual schema. This ensures every piece of information needed for future model training is captured atomically.

**Proposed `FeedbackEvents` Schema:**

```json
{
  "_id": "64c9e8f1a3b4c5d6e7f8g9h0", // Auto-generated ObjectID
  "timestamp": "2025-07-30T10:00:00Z", // ISODate of the event
  "user_id": "user123_session_abc", // Anonymized user or session ID

  "search_context": {
    "query_string": "patient with bloody vomit and low blood pressure",
    "filters_applied": {
      "system": "Cardiovascular System",
      "condition": "Shock"
    },
    "model_info": {
      "model_name": "BAAI/bge-large-en-v1.5",
      "model_phase": "baseline_v1"
    }
  },

  "retrieved_question_id": "fa06e587-fbeb-4277-9494-156cbcf72bd2", // Links to the Questions collection
  "rank": 3, // The position of this question in the result list (1-indexed)
  "user_feedback": "relevant" // Could be 'relevant' or 'not_relevant'
}
```

**Why this schema is so valuable:**

  * A **`relevant`** feedback event gives us a high-quality **positive pair**: `(search_context.query_string, retrieved_question_id)`.
  * A **`not_relevant`** feedback event gives us a high-quality **hard negative pair**, which is often even more valuable for teaching the model nuance.
  * Storing `filters_applied` and `model_info` allows us to slice and dice the data later and understand model performance under different conditions.

-----

### \#\# Designing the User-Facing Filtering UI 🎨

Your intuition is spot on. Presenting a massive, nested tree of all possible tags would be a user experience disaster. The standard and most effective solution here is to use **cascading (or dependent) dropdowns**.

This creates a guided and progressively disclosed filtering experience:

1.  **Initial State**: The user sees only one filter dropdown: **"System"**.
2.  **User Action**: The user selects "Cardiovascular System".
3.  **Dynamic Update**: A *second* dropdown, **"Condition"**, instantly appears. Its options are dynamically populated *only* with conditions relevant to the Cardiovascular System (e.g., "Shock," "Myocardial Infarction," "Arrhythmia").
4.  **User Action**: The user selects "Shock."
5.  **Dynamic Update**: A *third* dropdown, **"Subtype"**, appears, populated only with shock subtypes (e.g., "Hypovolemic," "Cardiogenic," "Septic").

The user can stop at any level. If they only select "Cardiovascular System" and "Shock," the filter applied and logged in the `FeedbackEvents` document would be `{ system: 'Cardiovascular System', condition: 'Shock' }`. The search would then correctly include all subtypes of shock within that system.

-----

### \#\# The Taxonomy: Flexibility and Future-Proofing 🌳

You are wise to anticipate that the taxonomy will evolve and may not be perfectly hierarchical. The best way to handle this is to think of it not as a rigid tree but as a system of **faceted search**.

  * **Hybrid Approach**: We can treat some categories as nested (like `system` → `condition`) and present them as cascading dropdowns. Other, more orthogonal categories (like `pathophysiology` or `pharmacology`) can be presented as separate, multi-select filter boxes that are independent of the main hierarchy. This gives users both guided discovery and flexible, powerful filtering.

  * **A Centralized Taxonomy**: To make this entire system maintainable and future-proof, the taxonomy itself should not be hard-coded. We should create a **third collection** in MongoDB, perhaps named `Taxonomies`.

    **`Taxonomies` Collection Example Document:**

    ```json
    {
      "facet_name": "system",
      "value": "Cardiovascular System",
      "parent_facet": null,
      "children": ["Shock", "Myocardial Infarction", "Arrhythmia"] // References 'condition' values
    }
    ```

    **The benefits of this approach are immense:**

    1.  The UI filtering options are **dynamically populated** by querying this `Taxonomies` collection.
    2.  The LLM's tagging process in Phase 1 would be prompted to **adhere to this centrally managed taxonomy**, ensuring consistency.
    3.  **Updating is easy**: If you want to add a new condition or rename a subtype, you only change it in the `Taxonomies` collection. The update automatically reflects in the UI without requiring any code changes. This makes the system incredibly agile and easy to maintain.


### \#\# Designing the Flexible `Taxonomies` Collection

The key to handling a non-rigid hierarchy is to model the taxonomy as a graph of nodes rather than a strict tree. Each document in the `Taxonomies` collection will represent a single tag or "node" and will define its relationship to other nodes. This approach gracefully handles varying depths.

**`Taxonomies` Schema:**

```json
{
  "_id": "cardio_shock_hypovolemic", // A unique, human-readable ID
  "display_name": "Hypovolemic Shock",
  "facet": "subtype", // The category of this tag (e.g., system, condition, subtype)
  "parent_id": "cardio_shock", // The ID of the parent node. Null for top-level nodes.
  "children_ids": [] // An array of IDs for direct children nodes.
}
```

**Example Documents:**

```javascript
// A top-level node (no parent)
db.Taxonomies.insertOne({
  _id: "cardio",
  display_name: "Cardiovascular System",
  facet: "system",
  parent_id: null,
  children_ids: ["cardio_shock", "cardio_mi"]
});

// A child node
db.Taxonomies.insertOne({
  _id: "cardio_shock",
  display_name: "Shock",
  facet: "condition",
  parent_id: "cardio",
  children_ids: ["cardio_shock_hypovolemic", "cardio_shock_cardiogenic"]
});

// A grandchild node
db.Taxonomies.insertOne({
  _id: "cardio_shock_hypovolemic",
  display_name: "Hypovolemic Shock",
  facet: "subtype",
  parent_id: "cardio_shock",
  children_ids: []
});

// A standalone, non-hierarchical facet
db.Taxonomies.insertOne({
  _id: "patho_baroreflex",
  display_name: "Baroreceptor Reflex",
  facet: "pathophysiology",
  parent_id: null,
  children_ids: []
});
```

This structure allows a "condition" like "Shock" to have "subtypes," while another condition might not. It also supports independent facets like "pathophysiology" that don't have parents or children.

-----

### \#\# Prompting Gemini 1.5 Pro to Adhere to the Taxonomy

You don't need to show the entire complex structure to the model for every question. The process is to first generate a simplified, text-based representation of the *entire* taxonomy one time. This text is then included in the system prompt for every API call to Gemini, serving as its rulebook.

**Step 1: Generate the Taxonomy "Rulebook" Text**

Your backend script will query the `Taxonomies` collection and format it into a clear, indented list.

```text
// Part of the generated rulebook text
...
- system: Cardiovascular System
  - condition: Shock
    - subtype: Hypovolemic Shock
    - subtype: Cardiogenic Shock
    - subtype: Septic Shock
  - condition: Myocardial Infarction
    - subtype: STEMI
    - subtype: NSTEMI
- system: Respiratory System
...
// Standalone facets
- pathophysiology: Baroreceptor Reflex
- pathophysiology: Apoptosis
...
```

**Step 2: Engineer the Prompt**

You will construct a prompt that includes the cleaned question text and specifically instructs the model to use the provided rulebook. The key is to demand a JSON output with a specific schema.

**Example Gemini 1.5 Pro Prompt:**

```
You are a medical expert AI. Your task is to analyze the provided medical question and assign relevant tags based *only* on the taxonomy provided in the 'Taxonomy Rulebook'.

**Taxonomy Rulebook:**
---
[Paste the rulebook text from Step 1 here]
---

**Medical Question:**
---
Title: Hypovolemic Shock from Hematemesis...
Case Presentation: A 52-year-old man...
[...rest of cleaned text...]
---

Analyze the question and respond with a JSON object containing a 'tags' array. Each object in the array must contain the 'id', 'display_name', and 'facet' of the most specific applicable tag from the rulebook. Include all relevant hierarchical paths and any applicable standalone facets.

**JSON Output Format:**
{
  "tags": [
    { "id": "...", "display_name": "...", "facet": "..." },
    ...
  ]
}
```

**How it handles varying depth:**
The model, by reading the entire case, will identify the most specific applicable tags. For one question, it might only be able to identify `"id": "cardio_shock"`. For another, more detailed question, it might identify `"id": "cardio_shock_hypovolemic"`. It might also identify a standalone tag like `"id": "patho_baroreflex"`. The prompt asks it to find all relevant tags, regardless of their depth or facet type. The LLM's output for each question will be an array of these tag objects, which you then store with the question.

-----

### \#\# Powering the Interactive Filtering UI

The front-end application interacts with the **`Taxonomies`** collection (not the LLM) to build the UI dynamically.

**Workflow for Cascading Dropdowns:**

1.  **Initial UI Load**: The front-end makes an API call to your backend: `GET /api/taxonomy/nodes?parent_id=null`. This queries the `Taxonomies` collection for all documents where `parent_id` is `null`.
2.  **Populate First Dropdown**: The API returns the top-level nodes (e.g., "Cardiovascular System," "Respiratory System," "Baroreceptor Reflex"). The UI uses this data to populate the initial filter controls.
3.  **User Selects an Option**: The user clicks on "Cardiovascular System" (which has the ID `"cardio"`).
4.  **Request Children Nodes**: The front-end triggers a new API call: `GET /api/taxonomy/nodes?parent_id=cardio`.
5.  **Populate Second Dropdown**: The backend queries the `Taxonomies` collection for all nodes whose `parent_id` is `"cardio"`. It returns the children (e.g., "Shock," "Myocardial Infarction"). The UI uses this response to create and populate the second dropdown for "Condition."

This process repeats for each level the user drills down. If a selected node has an empty `children_ids` array, no further dropdown is generated. This architecture is efficient, maintainable, and perfectly handles the varying depths and non-hierarchical facets defined in your flexible taxonomy.


***

### **Phase 1 Execution Blueprint: Foundational Semantic Search Engine**

**Objective:** To architect and deploy a robust, end-to-end baseline semantic search system. This phase will transform the raw, unstructured data from MongoDB into a clean, enriched, and indexed knowledge corpus. It will culminate in a functional Streamlit application that enables vector search, faceted filtering via a dynamic taxonomy, and captures user feedback to fuel future improvements.

---

### **Part 1: Foundational Taxonomy Development**

This initial part addresses the critical prerequisite of establishing a robust classification system. A well-designed taxonomy is the backbone of the filtering system and is essential for structured data enrichment.

**Step 1.1: Automated Taxonomy Scaffolding with an LLM**
We will leverage an LLM to perform the heavy lifting of creating a draft taxonomy, which is far more efficient than a manual, from-scratch effort.

* **Action:** Extract the clean text from a diverse, representative sample of 1,000-2,000 questions from the `Questions` collection.
* **Tool:** Gemini 1.5 Pro.
* **Process:** Construct a detailed prompt instructing the LLM to act as a medical curriculum designer. The prompt will ask it to analyze the provided sample of questions and identify recurring systems, clinical conditions, subtypes, and other key classifiers (like pathophysiology or pharmacology). Crucially, the prompt will command the LLM to output its proposed taxonomy directly into the structured JSON format required for our `Taxonomies` collection.
* **Outcome:** A machine-generated draft of the entire taxonomy, structured as a graph of nodes, ready for expert review.

**Step 1.2: Human Expert Review and Validation (Non-Negotiable)**
An LLM can create a great scaffold, but medical accuracy and pedagogical nuance require human expertise.

* **Action:** The JSON draft from the LLM will be presented to one or more medical domain experts for review.
* **Process:** The experts will validate the hierarchy, correct any clinical inaccuracies, merge redundant concepts, and refine the `display_name` of each tag for maximum clarity to the end-user. Their final approval signs off on the official v1 of the taxonomy.
* **Outcome:** A validated, expert-approved taxonomy structure.

**Step 1.3: Populate the `Taxonomies` Collection**
The final, approved structure is now persisted in the database.

* **Action:** Write a one-time script to parse the final taxonomy JSON and populate the `Taxonomies` collection in MongoDB according to the flexible, parent-child schema we designed previously.
* **Outcome:** A populated `Taxonomies` collection that will serve as the single source of truth for both the LLM tagging process and the front-end filtering UI.

---

### **Part 2: The Data Processing and Embedding Pipeline**

This is the core ETL (Extract, Transform, Load) workflow that processes every question in the database.

**Step 2.1: Extraction and Deterministic Cleaning**
* **Action:** Create a Python script that iterates through every document in the MongoDB `Questions` collection.
* **Tool:** `pymongo` for database connection, `BeautifulSoup` for HTML parsing.
* **Process:** For each document, extract the `question`, `choices` array, and `explanation` fields. Use `BeautifulSoup` to strip all HTML tags, converting them into clean, plain text. The unreliable `text` field in the source data will be ignored and rebuilt from scratch.
* **Outcome:** In-memory, clean text versions of the question body, each choice, and the full explanation for every question.

**Step 2.2: Unified Semantic Enrichment (Single LLM Call)**
This is the optimized, single-pass enrichment step.

* **Action:** For each question's cleaned text, construct a single, comprehensive prompt for Gemini 1.5 Pro.
* **Process:** The prompt will provide the cleaned text and the "Taxonomy Rulebook" (generated from the `Taxonomies` collection as described previously). It will instruct the LLM to return a single JSON object containing three distinct keys:
    1.  `title`: A concise, clinically relevant title for the question.
    2.  `key_learning_objective`: A one-sentence distillation of the core pedagogical point.
    3.  `tags`: An array of tag objects (`{id, display_name, facet}`) that accurately classify the question according to the provided rulebook.
* **Outcome:** A structured JSON object for each question containing all the high-value, LLM-generated semantic metadata.

**Step 2.3: Embedding Generation and Vector Indexing**
* **Action:** For each question, assemble the final, structured text document for embedding. This document will include the LLM-generated `title` and `key_learning_objective` along with the cleaned question body, choices, and explanation.
* **Tool:** The `sentence-transformers` library with the `BAAI/bge-large-en-v1.5` model.
* **Process:**
    1.  Pass the assembled text document to the `BGE` model's `encode` method to generate a 1024-dimension embedding vector.
    2.  Connect to your vector database (e.g., Weaviate, Pinecone).
    3.  For each question, `upsert` a record containing:
        * The unique question `_id` from the original MongoDB collection.
        * The generated embedding vector.
        * The `tags` array (from Step 2.2) as the metadata payload for filtering.
* **Outcome:** A fully populated and indexed vector database where every question is represented by a vector and is filterable by its expert-validated tags.

---

### **Part 3: Application Logic and Streamlit Integration**

With the data prepared, we now build the application components.

**Step 3.1: The Core Search & Filtering Function**
Since we are using Streamlit, we will build a robust Python function that encapsulates all search logic.

* **Action:** Create a Python function, e.g., `perform_search(query_string: str, filters: dict) -> list`.
* **Process:** This function will:
    1.  Take the user's free-text query and the dictionary of selected filters (e.g., `{'system': 'cardio', 'condition': 'cardio_shock'}`) as input.
    2.  If `query_string` is provided, encode it using the same `BGE` model.
    3.  Construct a single query to the vector database that performs a hybrid search: it finds the nearest vector neighbors to the encoded query string *while also* applying a metadata filter for the provided tags.
    4.  The function will return an ordered list of the original question `_id`s.
* **Outcome:** A well-tested, reusable function that serves as the brain of the search application.

**Step 3.2: The Human-in-the-Loop Feedback System**
* **Action:** Define the `FeedbackEvents` collection schema in MongoDB as previously designed. Create a function, e.g., `log_feedback(search_context: dict, question_id: str, user_id: str, feedback: str)`.
* **Process:** This function will handle the logic for persisting user feedback. It will use an **`upsert`** operation.
    * It will construct a unique query filter based on a combination of `user_id`, `question_id`, and a hash of the `search_context` object.
    * If a document matching this filter exists, it will simply update the `user_feedback` field (e.g., from "relevant" to "not_relevant").
    * If no document exists, it will create a new one.
* **Outcome:** A robust mechanism for capturing high-quality training data that correctly handles users changing their minds without creating duplicate entries.

**Step 3.3: Streamlit Frontend Integration**
* **Action:** Extend the existing Streamlit application to incorporate the new features.
* **Process:**
    1.  **Filtering UI:** Implement the cascading dropdowns. Use Streamlit's `st.session_state` to keep track of the user's selections at each level of the taxonomy. When a user selects from one dropdown, a callback function will be triggered to query the `Taxonomies` collection and populate the next dropdown in the hierarchy.
    2.  **Search Input:** Add an `st.text_input` for the free-text vector search. A search button will trigger the `perform_search` function.
    3.  **Results Display:** The application will loop through the returned list of question `_id`s, fetch the full question data from MongoDB, and display it.
    4.  **Feedback Buttons:** Next to each displayed result, use `st.columns` to place two buttons ("👍 Relevant", "👎 Not Relevant"). The `on_click` parameter for each button will call the `log_feedback` function with all the necessary contextual information.
* **Outcome:** A fully functional, interactive web application that delivers the complete Phase 1 user experience.
