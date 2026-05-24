/**
 * aiTaxonomy.js — AI Resource Classification & Normalization System
 *
 * Defines the canonical AI Type / AI SubType taxonomy and the mapping rules
 * that translate raw cloud resources (AWS, GCP, Azure) into normalized
 * AI categories.  Used by the AI Cost Dashboard, Recommendations engine,
 * and cost-allocation export pipelines.
 *
 * Hierarchy:
 *   AI Type (6)  →  AI SubType (2-4 per type)  →  Normalized Category (5 display buckets)
 */

// ── Canonical AI Types ───────────────────────────────────────────────────────
export const AI_TYPES = {
  inference: {
    label: 'Inference',
    description: 'Real-time and batch model inference calls',
    color: 'var(--d1)',
    displayBucket: 'Inference',
  },
  training: {
    label: 'Training / Fine-tune',
    description: 'Model training, fine-tuning, distillation, and RLHF',
    color: 'var(--d3)',
    displayBucket: 'Fine-tune / train',
  },
  evaluation: {
    label: 'Eval + Guardrails',
    description: 'Model evaluation, safety guardrails, and quality monitoring',
    color: 'var(--d4)',
    displayBucket: 'Eval + guardrails',
  },
  devtools: {
    label: 'Dev Tools (Seats)',
    description: 'AI-powered developer tooling with per-seat pricing',
    color: 'var(--d5)',
    displayBucket: 'Dev tools (seats)',
  },
  vector: {
    label: 'Vector + Storage',
    description: 'Vector databases, embedding storage, model artifacts, training data',
    color: 'var(--d2)',
    displayBucket: 'Vector + storage',
  },
  mlops: {
    label: 'MLOps',
    description: 'Model serving infrastructure, pipelines, registries',
    color: 'var(--d6)',
    displayBucket: 'Fine-tune / train', // rolls into training bucket for display
  },
};

// ── Canonical AI SubTypes ────────────────────────────────────────────────────
export const AI_SUBTYPES = {
  // Inference
  realtime:    { label: 'Real-time API',      aiType: 'inference',   description: 'Synchronous LLM API calls' },
  batch:       { label: 'Batch inference',    aiType: 'inference',   description: 'Async offline batch processing' },
  streaming:   { label: 'Streaming',          aiType: 'inference',   description: 'Token-streaming / SSE responses' },
  embedding:   { label: 'Embeddings',         aiType: 'inference',   description: 'Vector embedding generation' },
  multimodal:  { label: 'Multimodal',         aiType: 'inference',   description: 'Vision, audio, or cross-modal calls' },
  // Training
  pretrain:    { label: 'Pre-training',       aiType: 'training',    description: 'Foundation model training from scratch' },
  finetune:    { label: 'Fine-tuning',        aiType: 'training',    description: 'Task-specific supervised adaptation' },
  rlhf:        { label: 'RLHF',              aiType: 'training',    description: 'Reinforcement learning from human feedback' },
  distill:     { label: 'Distillation',       aiType: 'training',    description: 'Knowledge distillation to smaller model' },
  // Evaluation
  evals:       { label: 'Model evals',        aiType: 'evaluation',  description: 'Automated test-suite evaluation pipelines' },
  guardrails:  { label: 'Guardrails',         aiType: 'evaluation',  description: 'Safety, policy, and content filtering' },
  monitoring:  { label: 'LLM monitoring',    aiType: 'evaluation',  description: 'Drift detection and quality monitoring' },
  // Dev tools
  ide:         { label: 'IDE plugin',         aiType: 'devtools',    description: 'Copilot-style in-editor assistant' },
  platform:    { label: 'AI platform',        aiType: 'devtools',    description: 'Managed AI development / testing platform' },
  apiaccess:   { label: 'API access seat',    aiType: 'devtools',    description: 'Direct API seat license' },
  // Vector / storage
  vectordb:    { label: 'Vector database',    aiType: 'vector',      description: 'ANN search index (Pinecone, pgvector…)' },
  artifacts:   { label: 'Model artifacts',    aiType: 'vector',      description: 'Model weights, LoRA adapters, checkpoints' },
  datasets:    { label: 'Training datasets',  aiType: 'vector',      description: 'Labeled data storage and versioning' },
  // MLOps
  serving:     { label: 'Model serving',      aiType: 'mlops',       description: 'Inference infra, routing, load balancing' },
  pipelines:   { label: 'ML pipelines',      aiType: 'mlops',       description: 'Training / data-processing pipelines' },
  registry:    { label: 'Model registry',     aiType: 'mlops',       description: 'Model versioning and staged deployment' },
};

// ── Normalized Display Categories ─────────────────────────────────────────────
// Five buckets shown in the "Mix · by workload" donut.
export const DISPLAY_BUCKETS = [
  { key: 'inference',  label: 'Inference',            color: 'var(--d1)' },
  { key: 'training',   label: 'Fine-tune / train',    color: 'var(--d3)' },
  { key: 'evaluation', label: 'Eval + guardrails',    color: 'var(--d4)' },
  { key: 'devtools',   label: 'Dev tools (seats)',    color: 'var(--d5)' },
  { key: 'vector',     label: 'Vector + storage',     color: 'var(--d2)' },
];

// ── Vendor Chart Categories ────────────────────────────────────────────────────
// Five buckets shown in the "Spend by vendor" stacked-area chart legend.
export const VENDOR_CHART_CATEGORIES = [
  { key: 'anthropic',    label: 'Anthropic',         color: 'oklch(0.68 0.13 50)' },
  { key: 'openai',       label: 'OpenAI',            color: 'oklch(0.55 0.005 250)' },
  { key: 'cloud_gpu',    label: 'Cloud GPU',         color: 'oklch(0.75 0.14 80)' },
  { key: 'cursor_seats', label: 'Cursor seats',      color: 'oklch(0.60 0.10 210)' },
  { key: 'vector_tools', label: 'Vector + tools',    color: 'oklch(0.60 0.12 165)' },
];

// ── AWS Resource Mapping Rules ────────────────────────────────────────────────
// Each rule: { pattern, aiType, aiSubType, vendor, chartCategory }
export const AWS_RULES = [
  // Amazon Bedrock — third-party model APIs
  { pattern: /bedrock.*claude|claude.*bedrock/i,        aiType: 'inference', aiSubType: 'realtime',   vendor: 'anthropic',  chartCategory: 'anthropic'   },
  { pattern: /bedrock.*titan.*embed/i,                  aiType: 'inference', aiSubType: 'embedding',  vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  { pattern: /bedrock.*llama|bedrock.*meta/i,           aiType: 'inference', aiSubType: 'realtime',   vendor: 'meta',       chartCategory: 'cloud_gpu'   },
  { pattern: /bedrock.*mistral/i,                       aiType: 'inference', aiSubType: 'realtime',   vendor: 'mistral',    chartCategory: 'cloud_gpu'   },
  { pattern: /bedrock.*cohere/i,                        aiType: 'inference', aiSubType: 'embedding',  vendor: 'cohere',     chartCategory: 'vector_tools'},
  { pattern: /bedrock.*stability|bedrock.*sdxl/i,       aiType: 'inference', aiSubType: 'multimodal', vendor: 'stability',  chartCategory: 'cloud_gpu'   },
  { pattern: /bedrock/i,                                aiType: 'inference', aiSubType: 'realtime',   vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  // Amazon SageMaker
  { pattern: /sagemaker.*training|sagemaker.*train/i,   aiType: 'training',  aiSubType: 'finetune',   vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  { pattern: /sagemaker.*endpoint|sagemaker.*infer/i,   aiType: 'inference', aiSubType: 'realtime',   vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  { pattern: /sagemaker.*notebook/i,                    aiType: 'devtools',  aiSubType: 'platform',   vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  { pattern: /sagemaker.*pipeline/i,                    aiType: 'mlops',     aiSubType: 'pipelines',  vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  { pattern: /sagemaker.*feature/i,                     aiType: 'mlops',     aiSubType: 'registry',   vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  { pattern: /sagemaker/i,                              aiType: 'mlops',     aiSubType: 'serving',    vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  // EC2 GPU instances (training)
  { pattern: /ec2.*p4d|p4d\./i,                         aiType: 'training',  aiSubType: 'pretrain',   vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  { pattern: /ec2.*p3|p3\.|ec2.*p2/i,                   aiType: 'training',  aiSubType: 'finetune',   vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  { pattern: /ec2.*trn1|trn1\./i,                        aiType: 'training',  aiSubType: 'finetune',   vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  // EC2 GPU instances (inference)
  { pattern: /ec2.*g5|g5\.|ec2.*g4|g4dn\./i,            aiType: 'inference', aiSubType: 'realtime',   vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  { pattern: /ec2.*inf2|inf2\.|ec2.*inf1/i,              aiType: 'inference', aiSubType: 'batch',      vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  // S3 — AI artifact storage
  { pattern: /s3.*model|s3.*checkpoint|s3.*weight/i,     aiType: 'vector',    aiSubType: 'artifacts',  vendor: 'aws',        chartCategory: 'vector_tools'},
  { pattern: /s3.*dataset|s3.*train.*data/i,             aiType: 'vector',    aiSubType: 'datasets',   vendor: 'aws',        chartCategory: 'vector_tools'},
  // OpenSearch vector
  { pattern: /opensearch.*vector|aoss/i,                 aiType: 'vector',    aiSubType: 'vectordb',   vendor: 'aws',        chartCategory: 'vector_tools'},
  // Aurora pgvector
  { pattern: /aurora.*pgvector|rds.*pgvector/i,          aiType: 'vector',    aiSubType: 'vectordb',   vendor: 'aws',        chartCategory: 'vector_tools'},
  // AWS Batch — ML pipelines
  { pattern: /aws batch.*gpu|batch.*ml/i,                aiType: 'mlops',     aiSubType: 'pipelines',  vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  // Lambda — inference routing
  { pattern: /lambda.*infer|lambda.*llm|lambda.*ai/i,    aiType: 'mlops',     aiSubType: 'serving',    vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  // Comprehend, Rekognition — managed AI
  { pattern: /comprehend|rekognition|textract|transcribe/i,aiType:'inference', aiSubType: 'realtime',  vendor: 'aws',        chartCategory: 'cloud_gpu'   },
  // Step Functions — ML orchestration
  { pattern: /step.*function.*ml|step.*function.*train/i, aiType: 'mlops',    aiSubType: 'pipelines',  vendor: 'aws',        chartCategory: 'cloud_gpu'   },
];

// ── GCP Resource Mapping Rules ────────────────────────────────────────────────
export const GCP_RULES = [
  // Vertex AI
  { pattern: /vertex.*prediction|vertex.*endpoint/i,      aiType: 'inference', aiSubType: 'realtime',   vendor: 'google',     chartCategory: 'cloud_gpu'   },
  { pattern: /vertex.*training|vertex.*custom.*train/i,   aiType: 'training',  aiSubType: 'finetune',   vendor: 'google',     chartCategory: 'cloud_gpu'   },
  { pattern: /vertex.*batch.*predict/i,                   aiType: 'inference', aiSubType: 'batch',      vendor: 'google',     chartCategory: 'cloud_gpu'   },
  { pattern: /vertex.*pipeline/i,                         aiType: 'mlops',     aiSubType: 'pipelines',  vendor: 'google',     chartCategory: 'cloud_gpu'   },
  { pattern: /vertex.*feature/i,                          aiType: 'mlops',     aiSubType: 'registry',   vendor: 'google',     chartCategory: 'cloud_gpu'   },
  { pattern: /vertex.*workbench/i,                        aiType: 'devtools',  aiSubType: 'platform',   vendor: 'google',     chartCategory: 'cloud_gpu'   },
  { pattern: /vertex/i,                                   aiType: 'mlops',     aiSubType: 'serving',    vendor: 'google',     chartCategory: 'cloud_gpu'   },
  // Cloud TPU
  { pattern: /tpu.*v5|tpu.*v4|tpu.*v3/i,                  aiType: 'training',  aiSubType: 'pretrain',   vendor: 'google',     chartCategory: 'cloud_gpu'   },
  { pattern: /tpu/i,                                       aiType: 'training',  aiSubType: 'finetune',   vendor: 'google',     chartCategory: 'cloud_gpu'   },
  // GCE GPU instances
  { pattern: /compute.*a100|instance.*a100/i,              aiType: 'training',  aiSubType: 'pretrain',   vendor: 'google',     chartCategory: 'cloud_gpu'   },
  { pattern: /compute.*l4|compute.*t4|instance.*t4/i,      aiType: 'inference', aiSubType: 'realtime',   vendor: 'google',     chartCategory: 'cloud_gpu'   },
  { pattern: /compute.*v100|instance.*v100/i,              aiType: 'training',  aiSubType: 'finetune',   vendor: 'google',     chartCategory: 'cloud_gpu'   },
  // Gemini / Generative AI API
  { pattern: /gemini.*flash|gemini.*pro|generative.*language/i, aiType: 'inference', aiSubType: 'realtime', vendor: 'google',  chartCategory: 'cloud_gpu'   },
  { pattern: /text.*embedding.*gecko|embedding.*bison/i,   aiType: 'inference', aiSubType: 'embedding',  vendor: 'google',     chartCategory: 'vector_tools'},
  // BigQuery ML
  { pattern: /bigquery.*ml|bqml/i,                         aiType: 'evaluation',aiSubType: 'evals',      vendor: 'google',     chartCategory: 'cloud_gpu'   },
  // Vector Search / Matching Engine / AlloyDB
  { pattern: /matching engine|vector.*search/i,            aiType: 'vector',    aiSubType: 'vectordb',   vendor: 'google',     chartCategory: 'vector_tools'},
  { pattern: /alloydb.*pgvector|alloydb.*vector/i,         aiType: 'vector',    aiSubType: 'vectordb',   vendor: 'google',     chartCategory: 'vector_tools'},
  // GCS — AI artifacts
  { pattern: /storage.*model|gcs.*checkpoint|gcs.*weight/i,aiType: 'vector',    aiSubType: 'artifacts',  vendor: 'google',     chartCategory: 'vector_tools'},
  { pattern: /storage.*dataset|gcs.*train.*data/i,         aiType: 'vector',    aiSubType: 'datasets',   vendor: 'google',     chartCategory: 'vector_tools'},
  // Dataflow / Cloud Composer — ML pipelines
  { pattern: /dataflow.*ml|dataflow.*train|composer.*ml/i, aiType: 'mlops',     aiSubType: 'pipelines',  vendor: 'google',     chartCategory: 'cloud_gpu'   },
  // Cloud Functions — inference routing
  { pattern: /cloud.*function.*infer|cloud.*run.*llm/i,    aiType: 'mlops',     aiSubType: 'serving',    vendor: 'google',     chartCategory: 'cloud_gpu'   },
  // Natural Language API, Vision API, etc.
  { pattern: /natural.*language|vision.*api|speech.*to.*text|translation.*api/i, aiType: 'inference', aiSubType: 'realtime', vendor: 'google', chartCategory: 'cloud_gpu' },
];

// ── Azure Resource Mapping Rules ──────────────────────────────────────────────
export const AZURE_RULES = [
  // Azure OpenAI Service
  { pattern: /azure.*openai.*gpt-4|openai.*gpt-4/i,        aiType: 'inference', aiSubType: 'realtime',   vendor: 'openai',     chartCategory: 'openai'      },
  { pattern: /azure.*openai.*gpt-3/i,                      aiType: 'inference', aiSubType: 'realtime',   vendor: 'openai',     chartCategory: 'openai'      },
  { pattern: /azure.*openai.*embed|openai.*text-embed/i,   aiType: 'inference', aiSubType: 'embedding',  vendor: 'openai',     chartCategory: 'vector_tools'},
  { pattern: /azure.*openai.*dall-e|openai.*dall-e/i,      aiType: 'inference', aiSubType: 'multimodal', vendor: 'openai',     chartCategory: 'openai'      },
  { pattern: /azure.*openai/i,                             aiType: 'inference', aiSubType: 'realtime',   vendor: 'openai',     chartCategory: 'openai'      },
  // Azure Machine Learning
  { pattern: /azure.*ml.*compute.*gpu|machine.*learning.*gpu.*cluster/i, aiType: 'training', aiSubType: 'finetune', vendor: 'microsoft', chartCategory: 'cloud_gpu' },
  { pattern: /azure.*ml.*managed.*endpoint|machine.*learning.*endpoint/i,aiType: 'inference',aiSubType: 'realtime', vendor: 'microsoft', chartCategory: 'cloud_gpu' },
  { pattern: /azure.*ml.*pipeline|machine.*learning.*pipeline/i,         aiType: 'mlops',    aiSubType: 'pipelines',vendor: 'microsoft', chartCategory: 'cloud_gpu' },
  { pattern: /azure.*ml.*notebook|machine.*learning.*compute.*instance/i, aiType: 'devtools', aiSubType: 'platform',vendor: 'microsoft', chartCategory: 'cloud_gpu' },
  { pattern: /azure.*machine.*learning|azure.*ml/i,                      aiType: 'mlops',    aiSubType: 'serving',  vendor: 'microsoft', chartCategory: 'cloud_gpu' },
  // Azure VM — GPU series (training)
  { pattern: /virtual.*machine.*nc.*a100|vm.*nca100/i,                   aiType: 'training', aiSubType: 'pretrain', vendor: 'microsoft', chartCategory: 'cloud_gpu' },
  { pattern: /virtual.*machine.*nc.*v3|virtual.*machine.*nd.*a100/i,     aiType: 'training', aiSubType: 'finetune', vendor: 'microsoft', chartCategory: 'cloud_gpu' },
  { pattern: /virtual.*machine.*nc.*t4|virtual.*machine.*nv/i,           aiType: 'inference',aiSubType: 'realtime', vendor: 'microsoft', chartCategory: 'cloud_gpu' },
  // Azure Cognitive Services / AI Services
  { pattern: /cognitive.*services.*language|azure.*language/i,           aiType: 'inference',aiSubType: 'realtime', vendor: 'microsoft', chartCategory: 'cloud_gpu' },
  { pattern: /computer.*vision|form.*recognizer|document.*intelligence/i,aiType: 'inference',aiSubType: 'multimodal',vendor:'microsoft', chartCategory: 'cloud_gpu' },
  { pattern: /azure.*speech|speech.*service/i,                           aiType: 'inference',aiSubType: 'multimodal',vendor:'microsoft', chartCategory: 'cloud_gpu' },
  // Content Safety / Guardrails
  { pattern: /content.*safety|azure.*moderator/i,                        aiType: 'evaluation',aiSubType:'guardrails',vendor:'microsoft', chartCategory: 'cloud_gpu' },
  // Azure AI Search — vector
  { pattern: /azure.*ai.*search|cognitive.*search.*semantic|azure.*search.*vector/i, aiType:'vector', aiSubType:'vectordb', vendor:'microsoft', chartCategory:'vector_tools' },
  // Blob Storage — AI artifacts
  { pattern: /blob.*model.*weights|blob.*checkpoint|blob.*dataset/i,     aiType: 'vector',   aiSubType: 'artifacts', vendor: 'microsoft', chartCategory: 'vector_tools'},
  // Azure Databricks — ML pipelines
  { pattern: /azure.*databricks.*ml|databricks.*train/i,                 aiType: 'mlops',    aiSubType: 'pipelines', vendor: 'microsoft', chartCategory: 'cloud_gpu' },
  // Prompt Flow
  { pattern: /prompt.*flow|azure.*promptflow/i,                          aiType: 'evaluation',aiSubType:'evals',     vendor: 'microsoft', chartCategory: 'cloud_gpu' },
];

// ── Third-party Vendor Registry ───────────────────────────────────────────────
// For costs billed directly (not via a cloud provider marketplace)
export const VENDOR_REGISTRY = [
  { vendor: 'anthropic',      aiType: 'inference', aiSubType: 'realtime',   chartCategory: 'anthropic',    displayName: 'Anthropic'       },
  { vendor: 'openai',         aiType: 'inference', aiSubType: 'realtime',   chartCategory: 'openai',       displayName: 'OpenAI'          },
  { vendor: 'cohere',         aiType: 'inference', aiSubType: 'embedding',  chartCategory: 'vector_tools', displayName: 'Cohere'          },
  { vendor: 'mistral',        aiType: 'inference', aiSubType: 'realtime',   chartCategory: 'cloud_gpu',    displayName: 'Mistral AI'      },
  { vendor: 'together',       aiType: 'inference', aiSubType: 'realtime',   chartCategory: 'cloud_gpu',    displayName: 'Together AI'     },
  { vendor: 'replicate',      aiType: 'inference', aiSubType: 'realtime',   chartCategory: 'cloud_gpu',    displayName: 'Replicate'       },
  { vendor: 'perplexity',     aiType: 'inference', aiSubType: 'realtime',   chartCategory: 'cloud_gpu',    displayName: 'Perplexity'      },
  { vendor: 'groq',           aiType: 'inference', aiSubType: 'realtime',   chartCategory: 'cloud_gpu',    displayName: 'Groq'            },
  { vendor: 'pinecone',       aiType: 'vector',    aiSubType: 'vectordb',   chartCategory: 'vector_tools', displayName: 'Pinecone'        },
  { vendor: 'weaviate',       aiType: 'vector',    aiSubType: 'vectordb',   chartCategory: 'vector_tools', displayName: 'Weaviate'        },
  { vendor: 'chroma',         aiType: 'vector',    aiSubType: 'vectordb',   chartCategory: 'vector_tools', displayName: 'Chroma'          },
  { vendor: 'cursor',         aiType: 'devtools',  aiSubType: 'ide',        chartCategory: 'cursor_seats', displayName: 'Cursor',         isSeats: true, seatCost: 40 },
  { vendor: 'github_copilot', aiType: 'devtools',  aiSubType: 'ide',        chartCategory: 'cursor_seats', displayName: 'GitHub Copilot', isSeats: true, seatCost: 19 },
  { vendor: 'codeium',        aiType: 'devtools',  aiSubType: 'ide',        chartCategory: 'cursor_seats', displayName: 'Codeium',        isSeats: true, seatCost: 12 },
  { vendor: 'tabnine',        aiType: 'devtools',  aiSubType: 'ide',        chartCategory: 'cursor_seats', displayName: 'Tabnine',        isSeats: true, seatCost: 12 },
  { vendor: 'langsmith',      aiType: 'evaluation',aiSubType: 'monitoring', chartCategory: 'cloud_gpu',    displayName: 'LangSmith'       },
  { vendor: 'weights_biases', aiType: 'evaluation',aiSubType: 'monitoring', chartCategory: 'cloud_gpu',    displayName: 'Weights & Biases'},
  { vendor: 'arize',          aiType: 'evaluation',aiSubType: 'monitoring', chartCategory: 'cloud_gpu',    displayName: 'Arize AI'        },
];

// ── Classification function ───────────────────────────────────────────────────
/**
 * Classify a single cost record into AI Type + SubType + chart category.
 *
 * @param {object} record - { service, vendor, description, provider, resource_type }
 * @returns {{ aiType, aiSubType, chartCategory, displayName }}
 */
export function classifyAIResource(record = {}) {
  const { service = '', vendor = '', description = '', provider = '', resource_type = '' } = record;
  const text = [service, description, resource_type].join(' ');
  const p = (provider || '').toLowerCase().trim();

  // Pick the right rule set
  const rules =
    p === 'aws'   ? AWS_RULES   :
    p === 'gcp'   ? GCP_RULES   :
    p === 'azure' ? AZURE_RULES : [];

  for (const rule of rules) {
    if (rule.pattern.test(text)) {
      return {
        aiType:       rule.aiType,
        aiSubType:    rule.aiSubType,
        chartCategory:rule.chartCategory,
        vendor:       rule.vendor || vendor,
        displayName:  rule.vendor || vendor || service,
      };
    }
  }

  // Fall back to vendor registry for direct-billed costs
  const vendorKey = (vendor || '').toLowerCase().replace(/[^a-z0-9]/g, '_');
  const vReg = VENDOR_REGISTRY.find(v => v.vendor === vendorKey);
  if (vReg) {
    return {
      aiType:       vReg.aiType,
      aiSubType:    vReg.aiSubType,
      chartCategory:vReg.chartCategory,
      vendor:       vendorKey,
      displayName:  vReg.displayName,
      isSeats:      vReg.isSeats,
      seatCost:     vReg.seatCost,
    };
  }

  // Default — treat unknown as inference
  return {
    aiType:       'inference',
    aiSubType:    'realtime',
    chartCategory:'cloud_gpu',
    vendor:       vendor || 'unknown',
    displayName:  service || vendor || 'Unknown',
  };
}

/**
 * Aggregate cost records into workload-mix buckets (for the donut chart).
 *
 * @param {Array} records - array of classified cost records with `.cost` field
 * @returns {Array} [{ key, label, color, total, pct }]
 */
export function aggregateByWorkload(records = []) {
  const totals = {};
  let grand = 0;

  for (const r of records) {
    const c = classifyAIResource(r);
    const bucket = AI_TYPES[c.aiType]?.displayBucket
      ? DISPLAY_BUCKETS.find(b => b.label === AI_TYPES[c.aiType].displayBucket)?.key || c.aiType
      : c.aiType;

    totals[bucket] = (totals[bucket] || 0) + (r.cost || 0);
    grand += r.cost || 0;
  }

  return DISPLAY_BUCKETS.map(b => ({
    ...b,
    total: totals[b.key] || 0,
    pct:   grand > 0 ? (totals[b.key] || 0) / grand : 0,
  })).filter(b => b.total > 0);
}

/**
 * Aggregate cost records into chart categories (for the spend-by-source chart).
 *
 * @param {Array} records
 * @returns {{ [chartCategory]: number }}
 */
export function aggregateByChartCategory(records = []) {
  const out = {};
  for (const r of records) {
    const c = classifyAIResource(r);
    out[c.chartCategory] = (out[c.chartCategory] || 0) + (r.cost || 0);
  }
  return out;
}

/**
 * Classify a model name string into a tier label.
 */
export function modelTier(modelName = '') {
  const m = modelName.toLowerCase();
  if (m.includes('haiku') || m.includes('mini') || m.includes('nano') || m.includes('flash') || m.includes('3.5')) return 'workhorse';
  if (m.includes('opus') || m.includes('gpt-4o') && !m.includes('mini') || m.includes('sonnet-4') || m.includes('ultra')) return 'flagship';
  if (m.includes('embed') || m.includes('embedding')) return 'embed';
  return 'standard';
}

/**
 * Friendly labels for chart categories
 */
export function chartCategoryLabel(key) {
  return VENDOR_CHART_CATEGORIES.find(c => c.key === key)?.label || key;
}

export function chartCategoryColor(key) {
  return VENDOR_CHART_CATEGORIES.find(c => c.key === key)?.color || 'var(--muted)';
}
