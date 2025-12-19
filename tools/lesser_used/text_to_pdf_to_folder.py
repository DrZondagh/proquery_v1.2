from fpdf import FPDF
import os

# Dictionary of documents: keys are filenames, values are the text content
documents = {
    "Jacques_Malan_Job_Description.pdf": """
Position Title: Sweeper (Janitorial Staff)  
Department: Facilities Management  
Reports To: Facilities Supervisor  
Location: MediTest Headquarters, Anytown, USA  
Employment Type: Full-Time  

Job Summary:  
As a Sweeper at MediTest, you are responsible for maintaining a clean, safe, and hygienic environment in our medical testing facilities. Your role ensures that all areas, including labs, offices, restrooms, and common spaces, meet health and safety standards to support our mission of providing accurate at-home testing kits.  

Key Responsibilities:  
- Sweep, mop, and vacuum floors daily in high-traffic areas.  
- Empty trash bins and dispose of waste according to biohazard protocols.  
- Clean and sanitize restrooms, including toilets, sinks, and mirrors.  
- Restock supplies like paper towels, soap, and cleaning agents.  
- Report any maintenance issues, such as leaks or broken fixtures.  
- Assist with minor setup for company events or lab preparations.  
- Adhere to all safety guidelines, including proper use of PPE.  

Qualifications:  
- High school diploma or equivalent.  
- Previous experience in janitorial or cleaning roles preferred.  
- Ability to lift up to 50 lbs and stand for extended periods.  
- Strong attention to detail and reliability.  
- Must pass a background check and health screening.  

Compensation: Starting at $35,000 annually, plus benefits.  
    """,
    "Jacques_Malan_Warning_Letter.pdf": """
MediTest Employee Warning Notice  
Date: December 1, 2025  
Employee Name: Jacques Malan  
Employee ID: JM-0456  
Position: Sweeper  
Issued By: HR Manager, Elena Vargas  

Subject: Formal Warning - Engaging in Unauthorized Romantic Activities (Kissing DUDEs - Behind the Toilets)

Dear Jacques,  

This letter serves as a formal warning regarding an incident observed on November 15, 2025, where you were found engaging in unauthorized romantic activities-specifically, kissing a DUDE colleague-during your assigned duties behind the employee restrooms (toilets area). This behavior violates MediTest's Code of Conduct, Section 4.2 on Professionalism and Workplace Etiquette, as well as Section 7.1 on Time Management and Productivity.  

Explanation of Why This Is Not a Good Thing for Business:  
At MediTest, our core business revolves around providing reliable, hygienic medical testing solutions to customers who trust us with their health data and samples. Maintaining a professional environment is crucial to upholding our reputation and operational efficiency. Engaging in personal romantic activities like kissing during work hours, especially in non-designated areas such as behind the toilets, poses several risks and negative impacts on the business:  

1. Health and Safety Concerns: The area behind the toilets is a high-risk zone for biohazards, given its proximity to plumbing and waste systems. Such activities could lead to contamination or accidents, compromising the sterile conditions required for our lab operations. If an employee were injured or exposed to pathogens during unauthorized personal time, it could result in workers' compensation claims, increased insurance premiums, and potential regulatory violations from health authorities like OSHA. This directly affects our bottom line, as fines or shutdowns could halt production of testing kits, leading to revenue loss estimated at $50,000 per day of downtime.  

2. Productivity and Efficiency Losses: Work hours are dedicated to tasks that support our mission. Diverting time to personal activities disrupts schedules-for instance, if sweeping duties are delayed, it could lead to unclean labs, delaying test kit assembly by hours. In a company where precision is key (e.g., ensuring no contaminants in our COVID-19 or blood sugar testing kits), even minor delays cascade into supply chain issues, customer dissatisfaction, and lost sales. Studies show that workplace distractions reduce overall team productivity by up to 20%, which in our case could mean fewer kits shipped and a dip in quarterly profits.  

3. Impact on Team Morale and Professionalism: Romantic activities in visible or semi-public areas like behind the toilets can create discomfort among colleagues, fostering perceptions of favoritism or unprofessionalism. This erodes trust in leadership and could lead to higher turnover rates-our HR data indicates that unaddressed interpersonal issues increase resignation risks by 15%. For a growing company like MediTest, retaining talent is vital; losing skilled staff means recruitment costs of $5,000-$10,000 per hire, diverting funds from R&D for new products like our upcoming allergy testing line.  

4. Reputation and Legal Risks: If such behavior becomes public (e.g., via social media or complaints), it could tarnish MediTest's image as a serious health-focused entity. Customers expect us to model the hygiene we promote in our products. Legal ramifications, such as harassment claims if the activity was non-consensual or perceived as such, could result in lawsuits costing tens of thousands in settlements and legal fees, damaging investor confidence and stock value (if we go public).  

To prevent recurrence, you are required to attend a mandatory professionalism training session on December 10, 2025. Further incidents may lead to suspension or termination. Please sign below to acknowledge receipt and discuss any questions with HR.  

Sincerely,  
Elena Vargas  
HR Manager  

Employee Acknowledgment: _________________________ Date: __________
    """,
    "Jacques_Malan_Performance_Review.pdf": """
MediTest Annual Performance Review  
Employee Name: Jacques Malan  
Review Period: January 1, 2025 - December 1, 2025  
Reviewer: Facilities Supervisor, Mark Thompson  
Overall Rating: Meets Expectations (3/5)  

Strengths:  
- Consistently thorough in cleaning high-traffic areas, reducing reported slip hazards by 30%.  
- Reliable attendance, with zero unexcused absences.  
- Proactive in reporting maintenance issues, preventing two potential floods in the lab wing.  

Areas for Improvement:  
- Time management during shifts; occasional delays in completing restroom sanitation rounds.  
- Adherence to professional conduct-see recent warning for inappropriate behavior.  
- Could improve initiative in suggesting eco-friendly cleaning supplies.  

Goals for Next Year:  
- Complete all daily tasks within allocated time frames.  
- Participate in cross-training for basic lab support duties.  
- Achieve 100% compliance with company policies.  

Comments: Jacques is a solid team player, but focusing on professionalism will help advance his role.  
    """,
    "Jacques_Malan_Payslip.pdf": """
MediTest Payslip  
Pay Period: November 1-30, 2025  
Employee Name: Jacques Malan  
Employee ID: JM-0456  
Position: Sweeper  
Gross Pay: $2,916.67 (Annual Salary: $35,000 / 12)  

Earnings:  
- Base Salary: $2,916.67  
- Overtime (5 hours @ $15/hr): $75.00  
- Total Earnings: $2,991.67  

Deductions:  
- Federal Tax: $300.00  
- State Tax: $150.00  
- Health Insurance: $100.00  
- Retirement Contribution: $87.50  
- Total Deductions: $637.50  

Net Pay: $2,354.17  
Payment Method: Direct Deposit  
YTD Gross: $32,083.37  
YTD Net: $25,895.87  
    """,
    "Jacques_Malan_Benefits_Guide.pdf": """
MediTest Employee Benefits Guide - Personalized for Jacques Malan  
Effective Date: January 1, 2025  

At MediTest, we value our employees' well-being with a comprehensive benefits package tailored to support your health, finances, and work-life balance. As a Sweeper, you're eligible for the following made-up benefits:  

- Health Coverage: Full medical, dental, and vision insurance with no copay for at-home testing kits (including our exclusive "MediSniff" allergy tester). Family coverage at 50% company subsidy.  
- Wellness Perks: Free annual "MediGlow" health scan (a fictional full-body diagnostic kit) and gym membership reimbursement up to $500/year.  
- Retirement Savings: 401(k) with 4% company match, plus a "MediFuture" bonus where we match contributions with stock in fictional health gadgets.  
- Paid Time Off: 15 days vacation, 10 sick days, and "MediRecharge" days for mental health (up to 5/year).  
- Unique Perks: "Sweepstakes" program-enter monthly draws for free cleaning robots; plus discounted MediTest products (e.g., 20% off blood pressure monitors).  
- Education Support: Tuition reimbursement up to $2,000/year for courses in facilities management or hygiene certification.  

Contact HR for enrollment or questions. Benefits subject to change.
    """,
    "Jacques_Malan_Employee_Handbook.pdf": """
MediTest Employee Handbook - Excerpt for Jacques Malan  
Version: 2025 Edition  
Welcome Message: Welcome, Jacques! As a valued Sweeper, this handbook outlines policies to ensure a productive environment at MediTest.  

Key Sections:  
- Company Mission: Innovating at-home medical tests for better health outcomes.  
- Code of Conduct: Maintain professionalism; no personal activities during duties (e.g., no kissing or loitering behind toilets).  
- Work Hours: 8 AM-5 PM, with breaks; overtime eligible.  
- Safety Protocols: Use PPE; report hazards immediately.  
- Anti-Harassment Policy: Zero tolerance; report to HR.  
- Termination Grounds: Repeated violations, including productivity lapses.  
- Contact Info: HR at hr@meditest.com.  

Full handbook available on intranet. Sign to acknowledge: _________________________
    """,
    "Kim_Wiid_Job_Description.pdf": """
Position Title: Administrative Assistant  
Department: Operations  
Reports To: Operations Manager  
Location: MediTest Headquarters, Anytown, USA  
Employment Type: Full-Time  

Job Summary:  
As an Administrative Assistant at MediTest, you provide essential support to ensure smooth daily operations, from scheduling to data entry, helping our team deliver top-notch medical testing services.  

Key Responsibilities:  
- Manage calendars, emails, and meeting setups.  
- Handle filing, data entry for test kit orders, and supply inventory.  
- Assist with customer inquiries via phone and email.  
- Prepare reports on operational metrics.  
- Coordinate travel and event logistics.  
- Support HR with onboarding paperwork.  

Qualifications:  
- Associate's degree or equivalent experience.  
- Proficiency in Microsoft Office and basic CRM tools.  
- Excellent organizational and communication skills.  
- Ability to multitask in a fast-paced environment.  

Compensation: Starting at $42,000 annually, plus benefits.  
    """,
    "Kim_Wiid_Warning_Letter.pdf": """
MediTest Employee Warning Notice  
Date: December 1, 2025  
Employee Name: Kim Wiid  
Employee ID: KW-0789  
Position: Administrative Assistant  
Issued By: HR Manager, Elena Vargas  

Subject: Formal Warning for Made-Up Infraction - Excessive Use of Company Printer for Personal Novel Printing  

Dear Kim,  

This letter serves as a formal warning for repeatedly using the company printer to produce copies of your personal sci-fi novel manuscript during work hours, observed on multiple dates in November 2025. This violates Section 5.3 on Resource Usage and Section 7.1 on Productivity.  

Explanation of Why This Is Not a Good Thing for Business: (Full page as requested)  
MediTest relies on efficient resource management to keep costs low and focus on innovating medical tests. Misusing equipment like printers for personal projects drains supplies (ink and paper cost $0.10/page, totaling $200 in your case) and ties up shared resources, delaying critical tasks like printing shipping labels for test kits. This could slow order fulfillment, leading to customer complaints and a 5-10% drop in satisfaction scores, directly impacting repeat business worth $100,000 annually. Additionally, it sets a poor example, potentially encouraging others and reducing overall office morale. Legal risks include intellectual property issues if personal work mixes with company data, plus environmental waste contradicts our "GreenMedi" sustainability pledge. To rectify, limit printing to business needs; further misuse may lead to suspension. Attend resource training on December 15, 2025.  

Sincerely,  
Elena Vargas  

Employee Acknowledgment: _________________________ Date: __________
    """,
    "Kim_Wiid_Performance_Review.pdf": """
MediTest Annual Performance Review  
Employee Name: Kim Wiid  
Review Period: January 1, 2025 - December 1, 2025  
Reviewer: Operations Manager, Sarah Lee  
Overall Rating: Exceeds Expectations (4/5)  

Strengths:  
- Streamlined scheduling, reducing meeting conflicts by 40%.  
- Accurate data entry, minimizing order errors.  
- Strong customer service, handling 50+ inquiries weekly.  

Areas for Improvement:  
- Avoid personal use of company resources-see warning.  
- Enhance skills in advanced Excel for reporting.  

Goals for Next Year:  
- Lead a process improvement project.  
- Achieve certification in admin software.  

Comments: Kim is efficient and positive; addressing minor issues will make her indispensable.  
    """,
    "Kim_Wiid_Payslip.pdf": """
MediTest Payslip  
Pay Period: November 1-30, 2025  
Employee Name: Kim Wiid  
Employee ID: KW-0789  
Position: Administrative Assistant  
Gross Pay: $3,500.00 (Annual Salary: $42,000 / 12)  

Earnings:  
- Base Salary: $3,500.00  
- Bonus (Performance): $200.00  
- Total Earnings: $3,700.00  

Deductions:  
- Federal Tax: $370.00  
- State Tax: $185.00  
- Health Insurance: $120.00  
- Retirement Contribution: $105.00  
- Total Deductions: $780.00  

Net Pay: $2,920.00  
Payment Method: Direct Deposit  
YTD Gross: $38,500.00  
YTD Net: $30,360.00  
    """,
    "Kim_Wiid_Benefits_Guide.pdf": """
MediTest Employee Benefits Guide - Personalized for Kim Wiid  
Effective Date: January 1, 2025  

At MediTest, we value our employees' well-being with a comprehensive benefits package tailored to support your health, finances, and work-life balance. As an Administrative Assistant, you're eligible for the following made-up benefits:  

- Health Coverage: Full medical, dental, and vision insurance with no copay for at-home testing kits (including our exclusive "MediSniff" allergy tester). Family coverage at 50% company subsidy.  
- Wellness Perks: Free annual "MediGlow" health scan and gym membership reimbursement up to $500/year.  
- Retirement Savings: 401(k) with 4% company match, plus a "MediFuture" bonus where we match contributions with stock in fictional health gadgets.  
- Paid Time Off: 15 days vacation, 10 sick days, and "MediRecharge" days for mental health (up to 5/year).  
- Unique Perks: "AdminAce" program-free office supplies for home use; plus discounted MediTest products (e.g., 20% off blood pressure monitors).  
- Education Support: Tuition reimbursement up to $2,000/year for admin or business courses.  

Contact HR for enrollment or questions. Benefits subject to change.
    """,
    "Kim_Wiid_Employee_Handbook.pdf": """
MediTest Employee Handbook - Excerpt for Kim Wiid  
Version: 2025 Edition  
Welcome Message: Welcome, Kim! As a key Administrative Assistant, this handbook outlines policies to ensure a productive environment at MediTest.  

Key Sections:  
- Company Mission: Innovating at-home medical tests for better health outcomes.  
- Code of Conduct: Use resources responsibly; no personal printing projects.  
- Work Hours: 9 AM-6 PM, with flexible breaks.  
- Safety Protocols: Ergonomic setups; report office hazards.  
- Anti-Harassment Policy: Zero tolerance; report to HR.  
- Termination Grounds: Resource misuse or repeated violations.  
- Contact Info: HR at hr@meditest.com.  

Full handbook available on intranet. Sign to acknowledge: _________________________
    """,
    "Michael_Zondagh_Job_Description.pdf": """
Position Title: Lab Technician  
Department: Research & Development  
Reports To: Lab Supervisor  
Location: MediTest Headquarters, Anytown, USA  
Employment Type: Full-Time  

Job Summary:  
As a Lab Technician at MediTest, you conduct tests and quality checks on our medical kits, ensuring accuracy and compliance with health standards.  

Key Responsibilities:  
- Perform sample testing for kits like blood glucose monitors.  
- Calibrate equipment and record data accurately.  
- Assist in R&D for new products.  
- Maintain lab cleanliness and inventory.  
- Prepare reports on test results.  
- Follow safety protocols for biohazards.  

Qualifications:  
- Bachelor's in Biology or related field.  
- Lab experience preferred.  
- Attention to detail and analytical skills.  

Compensation: Starting at $55,000 annually, plus benefits.  
    """,
    "Michael_Zondagh_Warning_Letter.pdf": """
MediTest Employee Warning Notice  
Date: December 1, 2025  
Employee Name: Michael Zondagh  
Employee ID: MZ-1123  
Position: Lab Technician  
Issued By: HR Manager, Elena Vargas  

Subject: Formal Warning for Made-Up Infraction - Sneaking Extra Coffee Breaks in the Biohazard Storage Room  

Dear Michael,  

This letter serves as a formal warning for taking unauthorized extended coffee breaks in the biohazard storage room, noted on several occasions in November 2025. This breaches Section 6.4 on Safety and Section 7.1 on Productivity.  

Explanation of Why This Is Not a Good Thing for Business: (Full page as requested)  
MediTest's success hinges on strict safety in labs to avoid contamination in products like our DNA testing kits. Using restricted areas for breaks risks cross-contamination, potentially spoiling samples and leading to faulty kits shipped to customers-recall costs could exceed $100,000 per batch. It also violates FDA guidelines, inviting audits and fines up to $50,000, halting operations. Productivity suffers as breaks disrupt workflows, delaying R&D timelines by days and pushing back product launches, costing market share. Morale dips if rules seem unevenly enforced, increasing turnover in a specialized field where rehiring costs $15,000 per tech. To correct, stick to designated break areas; attend safety refresher on December 20, 2025.  

Sincerely,  
Elena Vargas  

Employee Acknowledgment: _________________________ Date: __________
    """,
    "Michael_Zondagh_Performance_Review.pdf": """
MediTest Annual Performance Review  
Employee Name: Michael Zondagh  
Review Period: January 1, 2025 - December 1, 2025  
Reviewer: Lab Supervisor, Dr. Lisa Chen  
Overall Rating: Meets Expectations (3/5)  

Strengths:  
- Accurate testing, with 98% quality pass rate.  
- Innovative suggestions for kit improvements.  
- Team collaborator in group projects.  

Areas for Improvement:  
- Better adherence to break policies-see warning.  
- Improve documentation speed.  

Goals for Next Year:  
- Lead a quality assurance initiative.  
- Obtain advanced lab certification.  

Comments: Michael's technical skills are strong; discipline will elevate his performance.  
    """,
    "Michael_Zondagh_Payslip.pdf": """
MediTest Payslip  
Pay Period: November 1-30, 2025  
Employee Name: Michael Zondagh  
Employee ID: MZ-1123  
Position: Lab Technician  
Gross Pay: $4,583.33 (Annual Salary: $55,000 / 12)  

Earnings:  
- Base Salary: $4,583.33  
- Shift Differential: $150.00  
- Total Earnings: $4,733.33  

Deductions:  
- Federal Tax: $473.00  
- State Tax: $237.00  
- Health Insurance: $150.00  
- Retirement Contribution: $137.50  
- Total Deductions: $997.50  

Net Pay: $3,735.83  
Payment Method: Direct Deposit  
YTD Gross: $50,416.63  
YTD Net: $39,593.13  
    """,
    "Michael_Zondagh_Benefits_Guide.pdf": """
MediTest Employee Benefits Guide - Personalized for Michael Zondagh  
Effective Date: January 1, 2025  

At MediTest, we value our employees' well-being with a comprehensive benefits package tailored to support your health, finances, and work-life balance. As a Lab Technician, you're eligible for the following made-up benefits:  

- Health Coverage: Full medical, dental, and vision insurance with no copay for at-home testing kits (including our exclusive "MediSniff" allergy tester). Family coverage at 50% company subsidy.  
- Wellness Perks: Free annual "MediGlow" health scan and gym membership reimbursement up to $500/year.  
- Retirement Savings: 401(k) with 4% company match, plus a "MediFuture" bonus where we match contributions with stock in fictional health gadgets.  
- Paid Time Off: 15 days vacation, 10 sick days, and "MediRecharge" days for mental health (up to 5/year).  
- Unique Perks: "LabLegend" program-free lab gear upgrades; plus discounted MediTest products (e.g., 20% off blood pressure monitors).  
- Education Support: Tuition reimbursement up to $2,000/year for science or tech courses.  

Contact HR for enrollment or questions. Benefits subject to change.
    """,
    "Michael_Zondagh_Employee_Handbook.pdf": """
MediTest Employee Handbook - Excerpt for Michael Zondagh  
Version: 2025 Edition  
Welcome Message: Welcome, Michael! As an essential Lab Technician, this handbook outlines policies to ensure a productive environment at MediTest.  

Key Sections:  
- Company Mission: Innovating at-home medical tests for better health outcomes.  
- Code of Conduct: Respect restricted areas; no unauthorized breaks in labs.  
- Work Hours: 7 AM-4 PM, with lab shifts.  
- Safety Protocols: Biohazard training mandatory.  
- Anti-Harassment Policy: Zero tolerance; report to HR.  
- Termination Grounds: Safety violations or productivity issues.  
- Contact Info: HR at hr@meditest.com.  

Full handbook available on intranet. Sign to acknowledge: _________________________
    """,
    "Wikus_JV_Rensburg_Job_Description.pdf": """
Position Title: Sales Representative  
Department: Sales & Marketing  
Reports To: Sales Director  
Location: MediTest Headquarters, Anytown, USA (with travel)  
Employment Type: Full-Time  

Job Summary:  
As a Sales Representative at MediTest, you promote and sell our medical testing kits to retailers, clinics, and online platforms, driving revenue growth.  

Key Responsibilities:  
- Prospect and close sales deals for products like pregnancy tests.  
- Build client relationships and conduct demos.  
- Track sales metrics and report weekly.  
- Attend trade shows and networking events.  
- Collaborate with marketing on campaigns.  
- Meet quarterly targets.  

Qualifications:  
- Bachelor's in Business or related.  
- 2+ years sales experience.  
- Strong negotiation and communication skills.  

Compensation: Starting at $60,000 annually, plus commission.  
    """,
    "Wikus_JV_Rensburg_Warning_Letter.pdf": """
MediTest Employee Warning Notice  
Date: December 1, 2025  
Employee Name: Wikus JV Rensburg  
Employee ID: WR-1345  
Position: Sales Representative  
Issued By: HR Manager, Elena Vargas  

Subject: Formal Warning for Made-Up Infraction - Using Company Car for Personal Joyrides to the Beach  

Dear Wikus,  

This letter serves as a formal warning for misusing the company vehicle for non-business trips, such as weekend beach outings, detected via GPS in November 2025. This contravenes Section 5.2 on Asset Usage and Section 8.3 on Ethics.  

Explanation of Why This Is Not a Good Thing for Business: (Full page as requested)  
MediTest invests in assets like vehicles to support sales efforts, not personal leisure. Unauthorized use increases mileage (adding $0.50/mile in maintenance), wear-and-tear, and insurance risks-if an accident occurs off-duty, claims could spike premiums by 20%, costing $10,000 yearly. It diverts resources from client visits, potentially missing sales opportunities worth $20,000 per deal, affecting revenue goals. Ethically, it erodes trust; if discovered by clients, it undermines our professional image in the health sector, leading to lost contracts. Broader impacts include tax compliance issues if mileage isn't tracked, inviting IRS audits and fines. To amend, restrict use to business; submit mileage logs weekly. Attend ethics workshop on December 25, 2025.  

Sincerely,  
Elena Vargas  

Employee Acknowledgment: _________________________ Date: __________
    """,
    "Wikus_JV_Rensburg_Performance_Review.pdf": """
MediTest Annual Performance Review  
Employee Name: Wikus JV Rensburg  
Review Period: January 1, 2025 - December 1, 2025  
Reviewer: Sales Director, Tom Harris  
Overall Rating: Exceeds Expectations (4/5)  

Strengths:  
- Exceeded sales targets by 25%, closing $500K in deals.  
- Excellent client rapport, securing repeat business.  
- Creative pitch strategies for new kits.  

Areas for Improvement:  
- Proper use of company assets-see warning.  
- Improve CRM data entry consistency.  

Goals for Next Year:  
- Hit 30% growth in territory sales.  
- Mentor junior reps.  

Comments: Wikus is a top performer; asset discipline will solidify his success.  
    """,
    "Wikus_JV_Rensburg_Payslip.pdf": """
MediTest Payslip  
Pay Period: November 1-30, 2025  
Employee Name: Wikus JV Rensburg  
Employee ID: WR-1345  
Position: Sales Representative  
Gross Pay: $5,000.00 (Annual Salary: $60,000 / 12)  

Earnings:  
- Base Salary: $5,000.00  
- Commission: $1,200.00  
- Total Earnings: $6,200.00  

Deductions:  
- Federal Tax: $620.00  
- State Tax: $310.00  
- Health Insurance: $150.00  
- Retirement Contribution: $150.00  
- Total Deductions: $1,230.00  

Net Pay: $4,970.00  
Payment Method: Direct Deposit  
YTD Gross: $55,000.00  
YTD Net: $43,470.00  
    """,
    "Wikus_JV_Rensburg_Benefits_Guide.pdf": """
MediTest Employee Benefits Guide - Personalized for Wikus JV Rensburg  
Effective Date: January 1, 2025  

At MediTest, we value our employees' well-being with a comprehensive benefits package tailored to support your health, finances, and work-life balance. As a Sales Representative, you're eligible for the following made-up benefits:  

- Health Coverage: Full medical, dental, and vision insurance with no copay for at-home testing kits (including our exclusive "MediSniff" allergy tester). Family coverage at 50% company subsidy.  
- Wellness Perks: Free annual "MediGlow" health scan and gym membership reimbursement up to $500/year.  
- Retirement Savings: 401(k) with 4% company match, plus a "MediFuture" bonus where we match contributions with stock in fictional health gadgets.  
- Paid Time Off: 15 days vacation, 10 sick days, and "MediRecharge" days for mental health (up to 5/year).  
- Unique Perks: "SalesStar" program-travel expense bonuses; plus discounted MediTest products (e.g., 20% off blood pressure monitors).  
- Education Support: Tuition reimbursement up to $2,000/year for sales or marketing courses.  

Contact HR for enrollment or questions. Benefits subject to change.
    """,
    "Wikus_JV_Rensburg_Employee_Handbook.pdf": """
MediTest Employee Handbook - Excerpt for Wikus JV Rensburg  
Version: 2025 Edition  
Welcome Message: Welcome, Wikus! As a dynamic Sales Representative, this handbook outlines policies to ensure a productive environment at MediTest.  

Key Sections:  
- Company Mission: Innovating at-home medical tests for better health outcomes.  
- Code of Conduct: Ethical use of assets; no personal vehicle trips.  
- Work Hours: Flexible with travel, but log accurately.  
- Safety Protocols: Road safety training for sales trips.  
- Anti-Harassment Policy: Zero tolerance; report to HR.  
- Termination Grounds: Ethics breaches or target misses.  
- Contact Info: HR at hr@meditest.com.  

Full handbook available on intranet. Sign to acknowledge: _________________________
    """
}

# Specify the output folder
output_folder = r"C:\Users\drzon\OneDrive\Documents\1. Business and admin\1. AI Chatbot\MediTest HR docs"

# Create the folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Function to generate PDF from text with text wrapping
def create_pdf(filename, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # Use multi_cell for automatic text wrapping
    pdf.multi_cell(190, 10, txt=content.strip())
    full_path = os.path.join(output_folder, filename)
    pdf.output(full_path)

# Generate all PDFs
for filename, content in documents.items():
    create_pdf(filename, content)

print("All individual PDFs have been generated with text wrapping and saved to the specified folder!")