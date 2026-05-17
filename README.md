# GoodEnoughLLMs

Fetches live LLM data from the [Artificial Analysis](https://artificialanalysis.ai) API and prints the top 5 models ranked by price/performance value score, for both agentic and coding tasks.

## What it does & why

The script computes a **value score** = Score Index / Price per 1M tokens, then ranks all models and prints the top 5 for each track.

### Agentic Track

The **Artificial Analysis Intelligence Index** is used as the performance metric because it weights agentic and coding tasks heavily: 25% Agents benchmarks (GDPval-AA + τ²-Bench Telecom) and 25% Coding benchmarks (Terminal-Bench Hard + SciCode), making 50% of the index directly relevant to agentic workloads.

> Artificial Analysis. (2026). *Intelligence Benchmarking Methodology*. Retrieved from <https://artificialanalysis.ai/methodology/intelligence-benchmarking#artificial-analysis-intelligence-index>

### Coding Track

The **Artificial Analysis Coding Index** (`artificial_analysis_coding_index`) is used as the performance metric. It directly measures coding capability across dedicated coding benchmarks. If this key is unpopulated for all models in the API response, the script exits with a clear error.

## Methodology

The script dynamically calculates a minimum score threshold of 80% of the highest available index value for each track. This ensures only top-tier models are ranked, regardless of how scores evolve over time as new models are released.

## Setup

```bash
pip install requests
export AA_KEY=your_api_key_here
```

## Usage

```bash
python aa_top5.py
```

Example output:

```
=== Agentic Track ===
Intel. Index threshold (80% of max 85.0): 68.0

Rank  Model                               Creator              Intel. Index   Price/1M  Value Score
----------------------------------------------------------------------------------------------------
1     ...                                 ...                         ...       ...          ...

=== Coding Track ===
Coding Index threshold (80% of max 72.0): 57.6

Rank  Model                               Creator              Coding Index   Price/1M  Value Score
----------------------------------------------------------------------------------------------------
1     ...                                 ...                         ...       ...          ...
```

## Limitations
The dedicated **Agentic Index** from Artificial Analysis is not available 
in the free API tier, as confirmed by inspecting all evaluation keys 
returned by the API:

```bash
curl -s https://artificialanalysis.ai/api/v2/data/llms/models \
  -H "x-api-key: $AA_KEY" \
  | jq '[.data[].evaluations | keys[]] | unique'
```

The returned keys contain no `artificial_analysis_agentic_index`. 
The Intelligence Index is used as the best available proxy, roughly 
50% of the index captures agentic capability.

## Data Source

Data provided by Artificial Analysis — https://artificialanalysis.ai/
