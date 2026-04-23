import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_faq_pdf(filename=None):
    if filename is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filename = os.path.join(project_root, "faq.pdf")
    
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Customer Support FAQ 2024")
    
    text = c.beginText(50, height - 100)
    text.setFont("Helvetica", 12)
    
    faqs = [
        "Q: What is the return policy?",
        "A: Items can be returned within 30 days of purchase with a receipt. Opened software cannot be returned.",
        "",
        "Q: How do I reset my account password?",
        "A: Go to the login page, click 'Forgot Password?', and enter the email address associated with your account.",
        "",
        "Q: What are your operating hours?",
        "A: Our support team is active from 9:00 AM to 5:00 PM EST, Monday through Friday.",
        "",
        "Q: How can I escalate a severe issue?",
        "A: For extreme emergencies, call our emergency line at 1-800-555-9999.",
        "Alternatively, you can ask this chatbot to speak with a manager.",
        "",
        "Q: Why is my dashboard not loading?",
        "A: Please clear your browser cache. If the issue persists, ensure your subscription is active.",
    ]
    
    for line in faqs:
        text.textLine(line)
        
    c.drawText(text)
    c.save()
    print(f"Created {filename}")

if __name__ == "__main__":
    create_faq_pdf()
