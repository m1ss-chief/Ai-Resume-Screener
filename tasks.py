import os
import smtplib
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from celery import Celery

load_dotenv()

#Celery
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = Celery("ats_mailer", broker=REDIS_URL, backend=REDIS_URL)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
)


SMTP_SERVER   = "localhost"
SMTP_PORT     = 1025            
SENDER_EMAIL  = "talent@resume-screener.com"

def send_email(to: str, subject: str, body: str) -> bool:
    msg = MIMEMultipart()
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = to
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(host=SMTP_SERVER, port=SMTP_PORT) as client:
            client.send_message(msg)
            client.quit()
        return True
    except Exception as e:
        print(f"  Failed to send email: {e}")
        return False


#Email Template

def build_email_body(candidate: dict, job_role: str, rank: int) -> str:
    strengths_html = "".join(
        f"<li>{s}</li>" for s in candidate.get("key_strengths", [])
    )

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto; padding: 20px;">

        <div style="background-color: #1a1a2e; padding: 20px; border-radius: 8px 8px 0 0;">
            <h2 style="color: white; margin: 0;">🎉 Congratulations, {candidate['candidate_name'].split()[0]}!</h2>
            <p style="color: #a0a0c0; margin: 4px 0 0 0; font-size: 13px;">ResumeScreener · AI-Powered Talent Acquisition</p>
        </div>

        <div style="background-color: #f9f9f9; padding: 24px; border: 1px solid #ddd; border-radius: 0 0 8px 8px;">

            <p>Dear <strong>{candidate['candidate_name']}</strong>,</p>

            <p>
                We are delighted to inform you that after a thorough AI-powered review of your profile,
                you have been <strong>shortlisted</strong> for the role of
                <strong>{job_role}</strong> at <strong>ResumeScreener</strong>.
            </p>

            <p>
                Out of all applicants evaluated, you ranked <strong>#{rank}</strong> with an
                ATS compatibility score of <strong>{candidate['ats_score']}/100</strong>.
            </p>

            <h3 style="color: #1a1a2e;">What stood out in your profile:</h3>
            <ul>
                {strengths_html}
            </ul>

            <h3 style="color: #1a1a2e;">Next Steps:</h3>
            <p>
                Our recruitment team will reach out to you within <strong>2 business days</strong>
                to schedule your interview. Please keep an eye on your inbox and ensure your
                calendar is available for the coming week.
            </p>

            <p>
                In the meantime, feel free to review the role requirements and prepare to
                discuss your experience with <strong>{', '.join(candidate['key_strengths'][:2])}</strong>.
            </p>

            <div style="background-color: #eef0fb; padding: 12px; border-left: 4px solid #1a1a2e; margin: 20px 0;">
                <p style="margin: 0;">
                    <strong>Role:</strong> {job_role}<br>
                    <strong>Company:</strong> ResumeScreener<br>
                    <strong>Website:</strong> www.resume-screener.com<br>
                    <strong>Interview Mode:</strong> To be communicated shortly
                </p>
            </div>

            <p>
                We look forward to speaking with you, {candidate['candidate_name'].split()[0]}.
                This is an exciting opportunity and we believe your skills align well with
                what we are building.
            </p>

            <p>Warm regards,<br>
            <strong>Talent Acquisition Team</strong><br>
            ResumeScreener<br>
            talent@resume-screener.com</p>

        </div>

        <p style="font-size: 11px; color: #999; text-align: center; margin-top: 16px;">
            This is an automated notification from ResumeScreener's AI-powered ATS system.
            Please do not reply to this email directly.
        </p>

    </body>
    </html>
    """


@app.task(bind=True, max_retries=3, default_retry_delay=10)
def send_shortlist_email(self, candidate: dict, job_role: str, rank: int):
    """
    Celery task: sends a personalized shortlist email to one candidate via MailHog.
    Retries up to 3 times if sending fails.
    """
    recipient_email = candidate["email"]
    candidate_name  = candidate["candidate_name"]

    print(f"\n  [Celery] Sending email to {candidate_name} <{recipient_email}>...")

    try:
        subject  = f" Congrats! You've Been Shortlisted for {job_role} | ResumeScreener"
        body     = build_email_body(candidate, job_role, rank)
        success  = send_email(recipient_email, subject, body)

        if success:
            print(f"  [Celery] Email sent to {candidate_name} — check http://localhost:8025")
            return {"status": "sent", "candidate": candidate_name, "email": recipient_email}
        else:
            raise Exception("send_email returned False")

    except Exception as exc:
        print(f"  [Celery] Failed for {candidate_name}: {exc}. Retrying...")
        raise self.retry(exc=exc)


def dispatch_shortlist_emails(top_3: list[dict], job_role: str):
    """
    Dispatches Celery tasks for all top 3 candidates asynchronously.
    Each email is queued as a separate task — non-blocking.
    """
    print(f"\n{'='*60}")
    print(f"  Dispatching shortlist emails for: {job_role}")
    print(f"{'='*60}")

    task_results = []
    for rank, candidate in enumerate(top_3, start=1):
        result = send_shortlist_email.delay(candidate, job_role, rank)
        task_results.append(result)
        print(f"  Queued email for #{rank} {candidate['candidate_name']} — Task ID: {result.id}")

    print(f"\n  Emails are sent to Top {len(top_3)} shortlisted candidates.")
    return task_results
