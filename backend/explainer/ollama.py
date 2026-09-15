import json
import requests
from ..config import settings

def _call_ollama(instruction: str, structured_evidence: dict) -> str:
    prompt = f'''You are an assistant to a cybersecurity examiner. Do not detect issues and do not invent facts, numbers, laws, regulations, assets, cases, or deadlines. Use only the supplied evidence. Clearly separate observed evidence from interpretation. Never mention JSON keys, database fields, implementation metadata, prompts, or model behavior. Do not infer facts beyond the exact records supplied. Return concise professional prose.

Task: {instruction}
Structured evidence:
{json.dumps(structured_evidence, indent=2, default=str)}
'''
    try:
        response = requests.post(settings.ollama_url, json={'model': settings.ollama_model, 'prompt': prompt, 'stream': False}, timeout=30)
        response.raise_for_status()
        result = response.json().get('response', '').strip()
        for forbidden in ('ai_generated', 'finding_type', 'detection_method', 'evidence_ids'):
            result = result.replace(forbidden, 'internal field')
        return result
    except requests.RequestException:
        return ''

def generate_assistant(action: str, finding: dict) -> tuple[str, bool]:
    instructions = {
        'explain': 'Explain this finding in three sections: Observed evidence, Why it matters, and Uncertainty / human checks required.',
        'recommend': 'Produce a prioritized corrective-action recommendation grounded only in the evidence. Include owner role, verification evidence, and an explicit human-review note.',
        'notice': 'Draft a supervisory show-cause notice containing organization, assessment reference, identified deficiency, supporting evidence, risk implication, requested clarification, requested corrective action, requested timeline placeholder, and evidence requested. Label it AI-generated draft requiring human review and authorization. Do not present it as a legal order.',
        'summary': 'Write a short executive summary using only the supplied findings and metrics, with no unsupported claims.',
    }
    result = _call_ollama(instructions.get(action, instructions['explain']), finding)
    if result:
        return f'AI-generated draft — requires human review and authorization.\n\n{result}', True
    return fallback_text(action, finding), False

def fallback_text(action: str, finding: dict) -> str:
    title = finding.get('title', 'identified control weakness')
    recommendation = finding.get('recommendation', 'Review the affected records and document corrective action.')
    if action == 'notice':
        return f'AI unavailable. Draft supervisory notice for human completion:\n\nSubject: Review required — {title}\n\nObserved evidence: {finding.get("description", "See linked evidence records.")}\nRequested action: {recommendation}\n\nAI-generated draft — requires human review and authorization. This is not a legal order.'
    if action == 'recommend':
        return f'AI unavailable. Evidence-backed recommendation:\n\n{recommendation}\n\nHuman review is required before authorization.'
    return f'AI unavailable. Evidence-backed finding:\n\n{finding.get("description", title)}\n\nHuman review is required before relying on this interpretation.'
