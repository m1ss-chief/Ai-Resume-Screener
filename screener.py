import json
import os
import google.generativeai as genai

#Configuration 
RESUMES_FILE = "resumes.json"
TOP_N        = 3

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-lite")

def load_resumes(filepath: str) -> list[dict]:
    with open(filepath, "r") as f:
        return json.load(f)


def build_prompt(resume: dict, job_role: str) -> str:
    """
    Builds the prompt sent to Gemini for a single candidate.
    Gemini is asked to return strict JSON so we can parse it reliably.
    """
    return f"""
You are an expert ATS (Applicant Tracking System) and technical recruiter.

Evaluate the following resume for the job role: **{job_role}**

Resume:
{json.dumps(resume, indent=2)}

Return ONLY a valid JSON object with exactly these fields (no markdown, no explanation, no ```json fences):
{{
  "candidate_id": "<id from resume>",
  "candidate_name": "<full name>",
  "ats_score": <integer 0-100>,
  "fit_summary": "<2-3 sentence summary of why they are or are not a good fit>",
  "key_strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "missing_skills": ["<skill 1>", "<skill 2>"],
  "recommendation": "<Strongly Recommended | Recommended | Maybe | Not Recommended>"
}}

Scoring guide:
- 85-100 : Excellent fit, meets almost all requirements
- 70-84  : Good fit, meets most requirements
- 50-69  : Partial fit, meets some requirements
- below 50: Poor fit

Be strict and objective. Vary scores meaningfully based on actual relevance to the role.
"""


def score_resume(resume: dict, job_role: str) -> dict:
    """Calls Gemini API for one resume and returns parsed result."""
    prompt = build_prompt(resume, job_role)

    response = model.generate_content(prompt)
    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


def screen_all(job_role: str) -> tuple[list[dict], list[dict]]:
    """
    Screens all resumes against the job role.
    Returns (all_results_sorted, top_3).
    """
    resumes = load_resumes(RESUMES_FILE)
    results = []

    print(f"\n{'='*60}")
    print(f"  Screening resumes for: {job_role}")
    print(f"{'='*60}\n")

    for resume in resumes:
        print(f"  Evaluating {resume['name']} ({resume['id']})...", end=" ", flush=True)
        try:
            result = score_resume(resume, job_role)
            result["email"] = resume["email"]
            results.append(result)
            print(f"Score: {result['ats_score']}  |  {result['recommendation']}")
        except Exception as e:
            print(f"ERROR - {e}")

    results.sort(key=lambda x: x["ats_score"], reverse=True)

    top_3 = results[:TOP_N]

    print(f"\n{'='*60}")
    print(f"  TOP {TOP_N} CANDIDATES FOR: {job_role}")
    print(f"{'='*60}")
    for rank, candidate in enumerate(top_3, start=1):
        print(f"\n  #{rank}  {candidate['candidate_name']}")
        print(f"       ATS Score   : {candidate['ats_score']}/100")
        print(f"       Fit Summary : {candidate['fit_summary']}")
        print(f"       Strengths   : {', '.join(candidate['key_strengths'])}")
        print(f"       Missing     : {', '.join(candidate['missing_skills']) or 'None'}")
        print(f"       Verdict     : {candidate['recommendation']}")

    return results, top_3

if __name__ == "__main__":
    job_role = input("Enter the job role to screen for: ").strip()
    all_results, top_3 = screen_all(job_role)

    output_file = f"screening_results_{job_role.replace(' ', '_').lower()}.json"
    with open(output_file, "w") as f:
        json.dump({"job_role": job_role, "all_candidates": all_results, "top_3": top_3}, f, indent=2)

    print(f"\n  Full results saved to: {output_file}")
