"""
Domain slug → escalation portals.
Each entry: (portal_name, url, one_line_description)
URLs verified as of March 2025.
"""

from typing import TypeAlias

EscalationEntry: TypeAlias = tuple[str, str, str]

ESCALATION_MAP: dict[str, list[EscalationEntry]] = {
    "e-commerce-online-shopping": [
        ("National Consumer Helpline (NCH)", "https://consumerhelpline.gov.in",
         "Call 1915 (toll-free) or file online. Companies respond within 15 days — start here first."),
        ("eDaakhil — Consumer Commission", "https://edaakhil.nic.in",
         "If NCH fails, file a formal consumer case with the District Commission online — no lawyer required."),
        ("Cyber Crime Portal", "https://cybercrime.gov.in",
         "For outright scams (fake seller took money and blocked you). Call 1930 to freeze funds immediately."),
    ],
    "banking-financial-services": [
        ("RBI Ombudsman (CMS)", "https://cms.rbi.org.in",
         "Escalate if bank doesn't resolve in 30 days. RBI forces refund of unauthorized transactions reported within 3 days."),
        ("NPCI Dispute Resolution", "https://www.npci.org.in/what-we-do/upi/dispute-redressal-mechanism",
         "Specifically for UPI/IMPS payments stuck, failed, or sent to wrong account."),
        ("Cyber Crime Portal", "https://cybercrime.gov.in",
         "Report financial fraud and unauthorized transfers — call 1930 immediately to freeze the transaction."),
    ],
    "real-estate-housing": [
        ("RERA — State Authority", "https://rera.gov.in",
         "Select your state RERA to file against builders for possession delays, defects, or deposit fraud."),
        ("eDaakhil — Consumer Commission", "https://edaakhil.nic.in",
         "For renter/landlord disputes and PG deposit theft — file without a lawyer."),
        ("National Consumer Helpline", "https://consumerhelpline.gov.in",
         "Call 1915 for quick mediation before escalating to commissions."),
    ],
    "government-services": [
        ("CPGRAMS (PM Grievance Portal)", "https://pgportal.gov.in",
         "Most effective for central govt departments (EPFO, Income Tax, Passport). Officials are mandated to respond."),
        ("RTI Online", "https://rtionline.gov.in",
         "File an RTI asking for daily progress on your pending application — forces stalled departments to act."),
        ("State CM Helplines", "https://pgportal.gov.in",
         "For local issues (ration cards, municipal bribes), use your state's CM helpline (e.g., 181 in UP/MP) or CPGRAMS."),
    ],
    "healthcare-pharmaceuticals": [
        ("National Medical Commission", "https://www.nmc.org.in/nmc-grievance",
         "Complaints against registered doctors for negligence, quackery, or ethical violations."),
        ("Insurance Ombudsman (CIO)", "https://www.cioins.co.in",
         "If your health insurance claim is unjustly denied, escalate here — the insurer is legally bound to respond."),
        ("CDSCO — Drug Safety", "https://cdscoonline.gov.in",
         "Report fake, expired, or substandard medicines and medical devices to the Central Drug Authority."),
    ],
    "education-recruitment": [
        ("National Consumer Helpline", "https://consumerhelpline.gov.in",
         "Primary route for EdTech scams (Byju's/Upgrad subscription traps, EMI mandates, misleading course ads)."),
        ("UGC e-Samadhan", "https://samadhan.ugc.ac.in",
         "For grievances against recognized universities — fee refunds, withheld certificates, and degree fraud."),
        ("Cyber Crime Portal", "https://cybercrime.gov.in",
         "Report fake job offers, visa scams, and 'pay to get an interview' recruitment frauds."),
    ],
    "telecom-internet": [
        ("TCCMS — Find Your Appellate Authority", "https://www.tccms.gov.in",
         "TRAI mandates a 2-tier complaint system. Use TCCMS to find your specific Jio/Airtel/Vi appellate authority."),
        ("Sanchar Saathi (DoT)", "https://sancharsaathi.gov.in",
         "Block stolen phones (CEIR), disconnect unknown SIMs registered to your Aadhaar (TAFCOP), and report fraud calls."),
        ("Cyber Crime Portal", "https://cybercrime.gov.in",
         "For SIM swap fraud, OTP theft, and cyber blackmail. Call 1930 to report financial losses."),
    ],
    "consumer-goods-services": [
        ("National Consumer Helpline", "https://consumerhelpline.gov.in",
         "Call 1915 for defective products, warranty denial, and service center fraud."),
        ("eDaakhil — Consumer Commission", "https://edaakhil.nic.in",
         "File a formal consumer case for product replacement, repair, or monetary compensation."),
        ("FSSAI — Food Safety (FoSCoS)", "https://foscos.fssai.gov.in",
         "Report adulterated food, expired products, and foreign objects found in packaged items."),
    ],
    "travel-logistics": [
        ("AirSewa (Ministry of Civil Aviation)", "https://airsewa.gov.in",
         "Most effective for airline complaints — flight cancellations, denied boarding, lost baggage. Airlines must respond."),
        ("RailMadad (Indian Railways)", "https://railmadad.indianrailways.gov.in",
         "Official complaints portal for train ticketing errors, TTE misconduct, refund issues, and on-board grievances."),
        ("National Consumer Helpline", "https://consumerhelpline.gov.in",
         "For courier delivery fraud, hotel aggregator (OYO/MakeMyTrip) refund delays, and bus booking issues."),
    ],
    "automobile-transport": [
        ("Insurance Ombudsman (CIO)", "https://www.cioins.co.in",
         "If your vehicle accident or damage claim is unjustly rejected, escalate to the Ombudsman immediately."),
        ("National Consumer Helpline", "https://consumerhelpline.gov.in",
         "Call 1915 for dealership fraud, inflated service bills, or accessories not delivered as promised."),
        ("eDaakhil — Consumer Commission", "https://edaakhil.nic.in",
         "File a formal case for manufacturing defects, seeking full vehicle replacement or compensation."),
    ],
    "utilities-energy": [
        ("CPGRAMS / CGRF", "https://pgportal.gov.in",
         "File via CPGRAMS or visit your state electricity board's Consumer Grievance Redressal Forum (CGRF) for unjustified bills."),
        ("National Consumer Helpline", "https://consumerhelpline.gov.in",
         "Call 1915 for LPG gas cylinder delivery issues, overcharging, and connection denial."),
        ("State CM Grievance Portals", "https://pgportal.gov.in",
         "For municipal water supply failure and garbage collection neglect — use CPGRAMS or your state's citizen portal."),
    ],
    "workplace-employment": [
        ("Samadhan Portal (Ministry of Labour)", "https://samadhan.labour.gov.in",
         "For industrial disputes, minimum wage denial, safety violations, and unjust termination under labour law."),
        ("EPFO IGMS", "https://epfigms.gov.in",
         "If employer blocks your PF withdrawal or transfer — EPFO will intervene directly with the employer."),
        ("Legal Notice (via Lawyer)", "https://consumerhelpline.gov.in",
         "For unpaid white-collar salaries, send a formal legal notice under the IBC. NCH can help identify free legal aid."),
    ],
}

FALLBACK_ESCALATION: list[EscalationEntry] = [
    ("National Consumer Helpline", "https://consumerhelpline.gov.in",
     "Call 1915 (toll-free) or file an online complaint against any company or service"),
    ("eDaakhil — Consumer Commission", "https://edaakhil.nic.in",
     "File a formal consumer case online without needing a lawyer"),
    ("Cyber Crime Portal", "https://cybercrime.gov.in",
     "Report online fraud — call 1930 (National Cyber Crime Helpline)"),
]
