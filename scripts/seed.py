"""Seed 8 domains and 42 categories into the database."""

import asyncio

from slugify import slugify
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Category, Domain, Company

DOMAINS: list[dict] = [
    {
        "name": "E-Commerce & Online Shopping",
        "icon": "🛒",
        "description": "Fraud and scams on online shopping platforms, fake sellers, and delivery issues.",
        "categories": [
            "Fake Product / Wrong Item Delivered",
            "Non-Delivery of Order",
            "Refund Not Processed",
            "Counterfeit / Duplicate Product",
            "Unauthorized Charges",
            "Seller Fraud",
            "Dropshipping Scam",
            "Fake Reviews / Deceptive Ratings",
            "Warranty Voided Unfairly",
            "Refurbished Sold as New",
            "Dark Patterns",
        ],
    },
    {
        "name": "Banking & Financial Services",
        "icon": "🏦",
        "description": "Banking fraud, unauthorized transactions, loan scams, and insurance mis-selling.",
        "categories": [
            "Unauthorized Transaction",
            "Phishing / Account Takeover",
            "Loan Fraud / Predatory Lending",
            "Insurance Mis-selling",
            "Credit Card Fraud",
            "UPI / Mobile Payment Fraud",
            "Investment / Ponzi Schemes",
            "ATM Card Skimming",
            "BNPL Hidden Charges",
            "KYC Fraud",
            "Forex / Crypto Scam",
        ],
    },
    {
        "name": "Real Estate & Housing",
        "icon": "🏠",
        "description": "Property fraud, builder defaults, rental scams, and land disputes.",
        "categories": [
            "Builder / Developer Fraud",
            "Rental Scam",
            "Land / Property Document Fraud",
            "Broker Fraud",
            "RERA Violation",
            "Possession Delay",
            "PG / Hostel Deposit Withheld",
            "Fake Listing / Bait-and-Switch",
            "Unfair Maintenance Charges",
            "Title Dispute / Encroachment",
            "Undisclosed Property Defects",
        ],
    },
    {
        "name": "Government Services",
        "icon": "🏛️",
        "description": "Corruption, bribery, impersonation of government officials, and service denial.",
        "categories": [
            "Bribery / Corruption",
            "Impersonation of Government Official",
            "Denial of Entitled Services",
            "Document Forgery",
            "Public Works Fraud",
            "Pension / Welfare Scheme Fraud",
            "Voter / Aadhaar Card Fraud",
            "Passport / Visa Processing Scam",
            "Traffic Challan Scam",
            "RTO / Driving License Extortion",
            "Income Tax Refund Scam",
        ],
    },
    {
        "name": "Healthcare & Pharmaceuticals",
        "icon": "🏥",
        "description": "Medical fraud, fake medicines, overcharging, and quackery.",
        "categories": [
            "Fake / Substandard Medicines",
            "Medical Overcharging",
            "Quackery / Unqualified Practitioner",
            "Insurance Claim Fraud",
            "Diagnostic Lab Fraud",
            "Misleading Health Products",
            "Online Pharmacy Scam",
            "Unnecessary Surgery / Procedures",
            "Fake Organ Donation Request",
            "Refusal to Treat in Emergency",
            "Miracle Cure / Magic Remedy Scam",
        ],
    },
    {
        "name": "Education & Recruitment",
        "icon": "🎓",
        "description": "Fake institutes, degree mills, job scams, and recruitment fraud.",
        "categories": [
            "Fake Job / Employment Offer",
            "Degree Mill / Fake Institute",
            "Coaching / Tuition Fraud",
            "Internship / Placement Scam",
            "Scholarship Fraud",
            "Immigration / Visa Job Scam",
            "EdTech Subscription Scam",
            "Paper Leak / Exam Fraud",
            "Withheld Original Certificates",
            "Study Abroad Consulting Fraud",
            "Data Selling by Institutes",
        ],
    },
    {
        "name": "Telecom & Internet",
        "icon": "📱",
        "description": "SIM swap fraud, fake tech support, internet service issues, and OTT scams.",
        "categories": [
            "SIM Swap / Cloning",
            "Fake Tech Support",
            "Unwanted Subscription / VAS Charges",
            "Internet Service Provider Fraud",
            "OTT Platform Scam",
            "Data Privacy Breach",
            "Task Fraud (Telegram / WhatsApp)",
            "Courier / Customs Scam",
            "Sextortion / Blackmail",
            "Dating / Matrimonial App Scam",
            "Social Media Account Hacking",
        ],
    },
    {
        "name": "Consumer Goods & Services",
        "icon": "📦",
        "description": "Defective products, misleading advertisements, service fraud, and warranty issues.",
        "categories": [
            "Defective Product",
            "Misleading Advertisement",
            "Warranty / After-sales Service Fraud",
            "Subscription / Membership Fraud",
            "Food Safety Violation",
            "Travel & Hospitality Fraud",
            "Packers and Movers Extortion",
            "Gym / Club Membership Scam",
            "Unfair Ticket Cancellation Policies",
            "Appliance Repair Scam",
            "Cab Surge / Ride-Hailing Extortion",
        ],
    },
    {
        "name": "Travel & Logistics",
        "icon": "✈️",
        "description": "Airline ticket issues, lost baggage, courier delays, missing parcels, and hotel/stay booking disputes.",
        "categories": [
            "Flight Cancellation / Denied Boarding",
            "Lost / Damaged Baggage",
            "Courier / Parcel Stolen in Transit",
            "Hotel Booking Denied",
            "Train / Bus Ticket Refund Failure",
            "Fake Travel Agent / Holiday Package Scam",
            "Overcharging by Airport / Railway Station Vendors",
            "Toll Plaza / Border Crossing Extortion",
        ],
    },
    {
        "name": "Automobile & Transport",
        "icon": "🚗",
        "description": "Defective vehicles, service center fraud, fake spare parts, and vehicle insurance denied.",
        "categories": [
            "Defective Vehicle Sold as New",
            "Service Center Overcharging",
            "Fake Spare Parts Used",
            "Vehicle Insurance Claim Denial",
            "RTO / Traffic Challan Extortion",
            "EV Battery / Range Misrepresentation",
            "Towing / Parking Extortion",
            "Selling Stolen / Accidental Vehicles",
            "Fastag Deduction Errors / Double Charges",
        ],
    },
    {
        "name": "Utilities & Energy",
        "icon": "⚡",
        "description": "Inflated electricity bills, power cuts, water supply issues, and LPG cylinder delivery scams.",
        "categories": [
            "Unjustified Bill Spike",
            "Frequent Unscheduled Power Cuts",
            "LPG Delivery Scam / Overcharging",
            "Irregular Water Supply",
            "Meter Tempering / Faulty Meters",
            "Solar Panel Installation Scam",
            "New Connection / Deposit Harassment",
            "Garbage Collection / Civic Services Neglect",
        ],
    },
    {
        "name": "Workplace & Employment",
        "icon": "🏢",
        "description": "Unpaid salaries, toxic workplace harassment, wrongful termination, and EPF withdrawal issues.",
        "categories": [
            "Unpaid Final Salary / F&F Settlement",
            "EPF / Gratuity Transfer Delayed",
            "Wrongful Termination",
            "Workplace Harassment / Toxic Culture",
            "Bond / Certificate Extortion",
            "Fake Background Verification Charges",
            "Non-payment of Minimum Wage / Overtime",
            "Maternity Benefit Denial",
            "Freelancer / Gig Worker Unpaid Invoices",
        ],
    },
]

COMPANIES = [
    "Amazon India", "Flipkart", "Meesho", "Myntra", "Ajio", "Nykaa", "Tata CLiQ",
    "Blinkit", "Zepto", "Swiggy Instamart", "JioMart", "Snapdeal", "FirstCry", "Croma",
    "Reliance Digital", "Reliance Smart", "BigBasket", "NNNOW", "Shopsy", "Purplle", 
    "Lenskart", "Bewakoof", "Pepperfry", "Shopclues", "Ferns N Petals", "Hopscotch", 
    "Decathlon", "Shoppers Stop",
    
    "State Bank of India (SBI)", "HDFC Bank", "ICICI Bank", "Axis Bank", 
    "Kotak Mahindra Bank", "Punjab National Bank (PNB)", "Bank of Baroda", 
    "Union Bank of India", "Canara Bank", "Bank of India", "IndusInd Bank", 
    "Yes Bank", "IDFC First Bank", "Paytm (One97 Communications)", "PhonePe",
    "Google Pay (GPay)", "Cred", "MobiKwik", "Amazon Pay", "BHIM / NPCI", 
    "Bajaj Finserv", "Navi", "Lazypay", "Simpl", "Slice", "Kissht", "Dhani", 
    "Muthoot Finance", "Manappuram Finance", "SBI Card", "LIC of India",
    
    "Lodha Group (Macrotech Developers)", "Godrej Properties", "DLF", 
    "Prestige Estates", "Sobha Limited", "Supertech", "Amrapali Group", 
    "Jaypee Infratech", "Unitech Group", "Puravankara", "Brigade Enterprises", 
    "Omaxe", "NoBroker", "MagicBricks", "99acres", "Housing.com", "Square Yards", 
    "Makaan", "Nestaway", "Stanza Living", "ZoloStays",

    "Indian Railways (IRCTC)", "India Post", "Employees' Provident Fund Organisation (EPFO)", 
    "Income Tax Department", "Unique Identification Authority of India (UIDAI / Aadhaar)", 
    "Passport Seva", "Regional Transport Office (RTO)", 
    "Municipal Corporation of Greater Mumbai (MCGM / BMC)", 
    "Municipal Corporation of Delhi (MCD)", "Bruhat Bengaluru Mahanagara Palike (BBMP)", 
    "Greater Chennai Corporation (GCC)", "State Traffic Police", "BSNL", "MTNL", 
    "State Electricity Boards", "Public Works Department (PWD)", 
    "Civil Supplies / Ration Distribution", "National Highway Authority of India (NHAI / FASTag)",

    "Apollo Hospitals", "Fortis Healthcare", "Max Healthcare", "Manipal Hospitals", 
    "Narayana Health", "Medanta", "Columbia Asia (Now Manipal)", "Care Hospitals", 
    "Practo", "PharmEasy", "1mg (Tata 1mg)", "Netmeds", "Apollo Pharmacy", 
    "Truemeds", "Dr. Lal PathLabs", "SRL Diagnostics", "Metropolis Healthcare", 
    "Thyrocare", "Star Health Insurance", "HDFC ERGO", "ICICI Lombard", 
    "Reliance General Insurance", "Niva Bupa Health Insurance", "Aditya Birla Capital",

    "Byju's", "Unacademy", "Physics Wallah", "Vedantu", "UpGrad", "Simplilearn", 
    "Udemy", "Coursera", "Allen Career Institute", "Aakash Educational Services", 
    "FIITJEE", "Resonance", "Great Learning", "Scaler Academy", "Masai School", 
    "Cuemath", "WhiteHat Jr", "LinkedIn (Recruitment Scams)", "Naukri.com", "Indeed", 
    "Foundit (Monster)", "Shine.com", "Apna", "Internshala",

    "Reliance Jio", "Bharti Airtel", "Vodafone Idea (Vi)", "ACT Fibernet", 
    "Hathway", "Excitel", "You Broadband", "Tata Play Fiber", "JioFiber", 
    "Airtel Xstream Fiber", "Netflix", "Amazon Prime Video", "Disney+ Hotstar", 
    "SonyLIV", "Zee5", "Spotify", "YouTube Premium",

    "Samsung India", "LG Electronics", "Sony India", "Whirlpool", "Apple India", 
    "Xiaomi", "OnePlus", "Boat", "Noise", "Realme", "Vivo", "Oppo", "Dell", 
    "HP (Hewlett-Packard)", "Lenovo", "Acer", "Asus", "Urban Company", "JustDial", 
    "Zomato", "Swiggy", "BookMyShow", "Paytm Insider", "Ticketmaster",

    "IndiGo", "Air India", "SpiceJet", "Vistara", "Akasa Air", "Air India Express", 
    "MakeMyTrip", "Goibibo", "Yatra", "Cleartrip", "EaseMyTrip", "Ixigo", "Oyo Rooms", 
    "Agoda", "Booking.com", "Airbnb", "IRCTC", "RedBus", "AbhiBus", "Delhivery", 
    "Blue Dart", "DTDC", "Ecom Express", "XpressBees", "Shadowfax", "India Post (Speed Post)",

    "Maruti Suzuki", "Hyundai Motor India", "Tata Motors", "Mahindra & Mahindra", 
    "Honda Cars India", "Toyota Kirloskar Motor", "Kia India", "Ola Electric", 
    "Ather Energy", "Royal Enfield", "Hero MotoCorp", "Honda Motorcycle and Scooter India", 
    "TVS Motor Company", "Bajaj Auto", "Skoda India", "Volkswagen India", "Uber", 
    "Ola Cabs", "Rapido", "Porter", "Zoomcar", "Revv", "BluSmart", "InDrive",

    "Adani Electricity", "Tata Power", "BESCOM (Bangalore)", "MSEDCL / Mahavitaran (Maharashtra)", 
    "BSES Rajdhani (Delhi)", "BSES Yamuna (Delhi)", "TANGEDCO (Tamil Nadu)", 
    "UPPCL (Uttar Pradesh)", "TSSPDCL (Telangana)", "Indane Gas", "Bharat Gas", 
    "HP Gas", "Mahanagar Gas (MGL)", "Indraprastha Gas (IGL)",

    "Tata Consultancy Services (TCS)", "Infosys", "Wipro", "HCLTech", "Tech Mahindra", 
    "Cognizant", "Accenture", "Capgemini", "Teleperformance", "Concentrix", "Genpact", 
    "IBM India", "L&T Technology Services", "Tech Support BPOs (Generic)", 
    "Deloitte India", "EY India", "KPMG India", "PwC India"
]


async def seed():
    async with AsyncSessionLocal() as session:
        for domain_data in DOMAINS:
            domain_slug = slugify(domain_data["name"])

            # Upsert domain
            result = await session.execute(select(Domain).where(Domain.slug == domain_slug))
            domain = result.scalar_one_or_none()

            if domain is None:
                domain = Domain(
                    name=domain_data["name"],
                    slug=domain_slug,
                    icon=domain_data["icon"],
                    description=domain_data["description"],
                )
                session.add(domain)
                await session.flush()  # get domain.id
                print(f"  + Domain: {domain.name}")
            else:
                print(f"  = Domain exists: {domain.name}")

            for cat_name in domain_data["categories"]:
                cat_slug = slugify(cat_name)
                result = await session.execute(
                    select(Category).where(
                        Category.domain_id == domain.id,
                        Category.slug == cat_slug,
                    )
                )
                cat = result.scalar_one_or_none()

                if cat is None:
                    cat = Category(domain_id=domain.id, name=cat_name, slug=cat_slug)
                    session.add(cat)
                    print(f"      + Category: {cat_name}")
                else:
                    print(f"      = Category exists: {cat_name}")

        for company_name in COMPANIES:
            result = await session.execute(
                select(Company).where(Company.name.ilike(company_name))
            )
            company = result.scalar_one_or_none()
            if not company:
                company = Company(name=company_name)
                session.add(company)
                print(f"  + Company: {company_name}")
            else:
                print(f"  = Company exists: {company_name}")

        await session.commit()
        print("\nSeeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
