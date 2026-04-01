import os
from dotenv import load_dotenv

load_dotenv()
import json
import time
from screener import screen_all
from tasks import dispatch_shortlist_emails


def print_banner():
    print("""
Welcome to Ai-Powered ResumeScreener.com
    """)


def check_env():
    required = {
        "GEMINI_API_KEY": "Gemini API key",
    }
    missing = []
    for var, desc in required.items():
        if not os.environ.get(var):
            missing.append(f"{var}  —  {desc}")

    if missing:
        print("Missing environment variables:\n")
        raise SystemExit(1)


def save_results(job_role: str, all_results: list, top_3: list):
    filename = f"results_{job_role.replace(' ', '_').lower()}.json"
    with open(filename, "w") as f:
        json.dump({
            "job_role"      : job_role,
            "total_screened": len(all_results),
            "all_candidates": all_results,
            "top_3_shortlisted": top_3
        }, f, indent=2)
    print(f"\nFull results saved to: {filename}")
    return filename

def print_final_summary(top_3: list, job_role: str):
    print(f"""
{'='*60}
  PIPELINE COMPLETE
{'='*60}
  Role Screened  : {job_role}
  Total Resumes  : 8
  Shortlisted    : {len(top_3)}
""")
    for rank, c in enumerate(top_3, start=1):
        print(f"  #{rank}  {c['candidate_name']}")
        print(f"       Score      : {c['ats_score']}/100")
        print(f"       Verdict    : {c['recommendation']}")
        print(f"       Email sent : {c['email']}\n")

    print("Emails sent to the Top 3 shortlisted candidates.")
    print(f"{'='*60}\n")


def run_pipeline():
    print_banner()
    check_env()

    print("  Enter the job role you want to screen candidates for.")
    # print("  Examples: Data Analyst | ML Engineer | SDE | AI Engineer\n")
    job_role = input("  Job Role > ").strip()

    if not job_role:
        print("Job role cannot be empty. Exiting.")
        raise SystemExit(1)

    print(f"\n  Starting AI screening pipeline for: {job_role}\n")
    time.sleep(1)

    all_results, top_3 = screen_all(job_role)

    save_results(job_role, all_results, top_3)

    print(f"\n  Ready to send shortlist emails to top {len(top_3)} candidates.")
    confirm = input("  Proceed with sending emails? (yes/no) > ").strip().lower()

    if confirm != "yes":
        print("\n  Email dispatch cancelled. Results saved. Exiting.")
        raise SystemExit(0)

    dispatch_shortlist_emails(top_3, job_role)
    print_final_summary(top_3, job_role)

if __name__ == "__main__":
    run_pipeline()
