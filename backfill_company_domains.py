"""
One-time script to backfill domain_id on existing companies.
Run this ONCE to fix companies that were seeded before the domain_id column existed.
"""
import asyncio
from slugify import slugify
from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models import Company, Domain

COMPANY_DOMAIN_MAP: dict[str, str] = {}

# Build the map from seed data
COMPANIES_BY_DOMAIN: dict[str, list[str]] = {
    "e-commerce-online-shopping": [
        "Amazon India", "Flipkart", "Meesho", "Myntra", "Ajio", "Nykaa", "Tata CLiQ",
        "Blinkit", "Zepto", "Swiggy Instamart", "JioMart", "Snapdeal", "FirstCry", "Croma",
        "Reliance Digital", "Reliance Smart", "BigBasket", "NNNOW", "Shopsy", "Purplle",
        "Lenskart", "Bewakoof", "Pepperfry", "Shopclues", "Ferns N Petals", "Hopscotch",
        "Decathlon", "Shoppers Stop",
    ],
    "banking-financial-services": [
        "State Bank of India (SBI)", "HDFC Bank", "ICICI Bank", "Axis Bank",
        "Kotak Mahindra Bank", "Punjab National Bank (PNB)", "Bank of Baroda",
        "Union Bank of India", "Canara Bank", "Bank of India", "IndusInd Bank",
        "Yes Bank", "IDFC First Bank", "Paytm (One97 Communications)", "PhonePe",
        "Google Pay (GPay)", "Cred", "MobiKwik", "Amazon Pay", "BHIM / NPCI",
        "Bajaj Finserv", "Navi", "Lazypay", "Simpl", "Slice", "Kissht", "Dhani",
        "Muthoot Finance", "Manappuram Finance", "SBI Card", "LIC of India",
    ],
    "real-estate-housing": [
        "Lodha Group (Macrotech Developers)", "Godrej Properties", "DLF",
        "Prestige Estates", "Sobha Limited", "Supertech", "Amrapali Group",
        "Jaypee Infratech", "Unitech Group", "Puravankara", "Brigade Enterprises",
        "Omaxe", "NoBroker", "MagicBricks", "99acres", "Housing.com", "Square Yards",
        "Makaan", "Nestaway", "Stanza Living", "ZoloStays",
    ],
    "government-services": [
        "Indian Railways (IRCTC)", "India Post", "Employees' Provident Fund Organisation (EPFO)",
        "Income Tax Department", "Unique Identification Authority of India (UIDAI / Aadhaar)",
        "Passport Seva", "Regional Transport Office (RTO)",
        "Municipal Corporation of Greater Mumbai (MCGM / BMC)",
        "Municipal Corporation of Delhi (MCD)", "Bruhat Bengaluru Mahanagara Palike (BBMP)",
        "Greater Chennai Corporation (GCC)", "State Traffic Police", "BSNL", "MTNL",
        "State Electricity Boards", "Public Works Department (PWD)",
        "Civil Supplies / Ration Distribution", "National Highway Authority of India (NHAI / FASTag)",
    ],
    "healthcare-pharmaceuticals": [
        "Apollo Hospitals", "Fortis Healthcare", "Max Healthcare", "Manipal Hospitals",
        "Narayana Health", "Medanta", "Columbia Asia (Now Manipal)", "Care Hospitals",
        "Practo", "PharmEasy", "1mg (Tata 1mg)", "Netmeds", "Apollo Pharmacy",
        "Truemeds", "Dr. Lal PathLabs", "SRL Diagnostics", "Metropolis Healthcare",
        "Thyrocare", "Star Health Insurance", "HDFC ERGO", "ICICI Lombard",
        "Reliance General Insurance", "Niva Bupa Health Insurance", "Aditya Birla Capital",
    ],
    "education-recruitment": [
        "Byju's", "Unacademy", "Physics Wallah", "Vedantu", "UpGrad", "Simplilearn",
        "Udemy", "Coursera", "Allen Career Institute", "Aakash Educational Services",
        "FIITJEE", "Resonance", "Great Learning", "Scaler Academy", "Masai School",
        "Cuemath", "WhiteHat Jr", "LinkedIn (Recruitment Scams)", "Naukri.com", "Indeed",
        "Foundit (Monster)", "Shine.com", "Apna", "Internshala",
    ],
    "telecom-internet": [
        "Reliance Jio", "Bharti Airtel", "Vodafone Idea (Vi)", "ACT Fibernet",
        "Hathway", "Excitel", "You Broadband", "Tata Play Fiber", "JioFiber",
        "Airtel Xstream Fiber", "Netflix", "Amazon Prime Video", "Disney+ Hotstar",
        "SonyLIV", "Zee5", "Spotify", "YouTube Premium",
    ],
    "consumer-goods-services": [
        "Samsung India", "LG Electronics", "Sony India", "Whirlpool", "Apple India",
        "Xiaomi", "OnePlus", "Boat", "Noise", "Realme", "Vivo", "Oppo", "Dell",
        "HP (Hewlett-Packard)", "Lenovo", "Acer", "Asus", "Urban Company", "JustDial",
        "Zomato", "Swiggy", "BookMyShow", "Paytm Insider", "Ticketmaster",
    ],
    "travel-logistics": [
        "IndiGo", "Air India", "SpiceJet", "Vistara", "Akasa Air", "Air India Express",
        "MakeMyTrip", "Goibibo", "Yatra", "Cleartrip", "EaseMyTrip", "Ixigo", "Oyo Rooms",
        "Agoda", "Booking.com", "Airbnb", "IRCTC", "RedBus", "AbhiBus", "Delhivery",
        "Blue Dart", "DTDC", "Ecom Express", "XpressBees", "Shadowfax", "India Post (Speed Post)",
    ],
    "automobile-transport": [
        "Maruti Suzuki", "Hyundai Motor India", "Tata Motors", "Mahindra & Mahindra",
        "Honda Cars India", "Toyota Kirloskar Motor", "Kia India", "Ola Electric",
        "Ather Energy", "Royal Enfield", "Hero MotoCorp", "Honda Motorcycle and Scooter India",
        "TVS Motor Company", "Bajaj Auto", "Skoda India", "Volkswagen India", "Uber",
        "Ola Cabs", "Rapido", "Porter", "Zoomcar", "Revv", "BluSmart", "InDrive",
    ],
    "utilities-energy": [
        "Adani Electricity", "Tata Power", "BESCOM (Bangalore)", "MSEDCL / Mahavitaran (Maharashtra)",
        "BSES Rajdhani (Delhi)", "BSES Yamuna (Delhi)", "TANGEDCO (Tamil Nadu)",
        "UPPCL (Uttar Pradesh)", "TSSPDCL (Telangana)", "Indane Gas", "Bharat Gas",
        "HP Gas", "Mahanagar Gas (MGL)", "Indraprastha Gas (IGL)",
    ],
    "workplace-employment": [
        "Tata Consultancy Services (TCS)", "Infosys", "Wipro", "HCLTech", "Tech Mahindra",
        "Cognizant", "Accenture", "Capgemini", "Teleperformance", "Concentrix", "Genpact",
        "IBM India", "L&T Technology Services", "Tech Support BPOs (Generic)",
        "Deloitte India", "EY India", "KPMG India", "PwC India",
    ],
}


async def backfill():
    async with AsyncSessionLocal() as session:
        # Load all domains into a slug→id map
        result = await session.execute(select(Domain))
        domain_map = {d.slug: d.id for d in result.scalars().all()}
        print(f"Loaded {len(domain_map)} domains.")

        updated = 0
        for domain_slug, company_names in COMPANIES_BY_DOMAIN.items():
            domain_id = domain_map.get(domain_slug)
            if not domain_id:
                print(f"  ! Domain not found: {domain_slug}")
                continue

            for company_name in company_names:
                # Find existing company with this name (regardless of domain_id)
                result = await session.execute(
                    select(Company).where(Company.name.ilike(company_name))
                )
                companies = result.scalars().all()

                for company in companies:
                    if company.domain_id is None:
                        company.domain_id = domain_id
                        updated += 1
                        print(f"  ✓ Updated [{domain_slug}]: {company.name}")
                    elif company.domain_id == domain_id:
                        print(f"  = Already correct: {company.name}")
                    else:
                        print(f"  ? Different domain_id on {company.name} — skipping")

        await session.commit()
        print(f"\nDone! Updated {updated} companies.")


if __name__ == "__main__":
    asyncio.run(backfill())
