"""AGLC4 reference data — extracted from the Australian Guide to Legal Citation (4th ed, 2018).

This module is the single source of truth for all AGLC4 lookups:
- Report series → bracket type (round vs square)
- Court identifiers → bracket type
- Jurisdiction abbreviations
- Pinpoint abbreviations
- Journal name abbreviations (common Australian)

Import this module in your validators and parsers. Never hardcode AGLC4 data elsewhere.
"""

# =============================================================================
# BRACKET TYPE: "round" = year-of-decision (1992), "square" = volume-based [2017]
#
# RULE 2.2.3: Reported decisions use round brackets when the year identifies the volume.
# RULE 2.3.1: Medium-neutral citations (MNC) ALWAYS use square brackets for the year.
# =============================================================================

# Authorised and commonly used Australian report series
# Source: AGLC4 s 2.2.3, Appendix A
REPORT_SERIES: dict[str, dict] = {
    # === HIGH COURT ===
    "CLR":   {"full_name": "Commonwealth Law Reports", "brackets": "round", "court": "HCA", "years": "1903–"},
    "ALJR":  {"full_name": "Australian Law Journal Reports", "brackets": "round", "court": "HCA", "years": "1927–"},

    # === FEDERAL COURT ===
    "FCR":   {"full_name": "Federal Court Reports", "brackets": "round", "court": "FCA", "years": "1984–"},
    "FLR":   {"full_name": "Federal Law Reports", "brackets": "round", "court": "various", "years": "1956–"},

    # === GENERALIST UNAUTHORISED ===
    "ALR":   {"full_name": "Australian Law Reports", "brackets": "round", "court": "various", "years": "1973–"},

    # === STATE/TERRITORY AUTHORISED REPORTS ===
    # ACT
    "ACTR":    {"full_name": "Australian Capital Territory Reports (in ALR)", "brackets": "round", "court": "ACTSC", "years": "1973–2008"},
    "ACTLR":   {"full_name": "Australian Capital Territory Law Reports", "brackets": "round", "court": "ACTSC", "years": "2007–"},

    # NSW
    "SR (NSW)": {"full_name": "State Reports (New South Wales)", "brackets": "round", "court": "NSWSC", "years": "1901–59"},
    "NSWR":     {"full_name": "New South Wales Reports", "brackets": "round", "court": "NSWSC", "years": "1960–70"},
    "NSWLR":    {"full_name": "New South Wales Law Reports", "brackets": "round", "court": "NSWSC", "years": "1971–"},

    # NT
    "NTR":   {"full_name": "Northern Territory Reports (in ALR)", "brackets": "round", "court": "NTSC", "years": "1979–91"},
    "NTLR":  {"full_name": "Northern Territory Law Reports", "brackets": "round", "court": "NTSC", "years": "1990–"},

    # QLD
    "St R Qd": {"full_name": "State Reports (Queensland)", "brackets": "round", "court": "QSC", "years": "1902–57"},
    "Qd R":    {"full_name": "Queensland Reports", "brackets": "square", "court": "QSC", "years": "1958–"},

    # SA
    "SALR": {"full_name": "South Australian Law Reports", "brackets": "round", "court": "SASC", "years": "1899–1920"},
    "SASR": {"full_name": "South Australian State Reports", "brackets": "round", "court": "SASC", "years": "1921–"},

    # TAS
    "Tas LR": {"full_name": "Tasmanian Law Reports", "brackets": "round", "court": "TASSC", "years": "1904–40"},
    "Tas SR": {"full_name": "Tasmanian State Reports", "brackets": "round", "court": "TASSC", "years": "1941–78"},
    "Tas R":  {"full_name": "Tasmanian Reports", "brackets": "round", "court": "TASSC", "years": "1979–"},

    # VIC
    "VLR": {"full_name": "Victorian Law Reports", "brackets": "round", "court": "VSC", "years": "1875–1956"},
    "VR":  {"full_name": "Victorian Reports", "brackets": "round", "court": "VSC", "years": "1957–"},

    # WA
    "WALR": {"full_name": "Western Australian Law Reports", "brackets": "round", "court": "WASC", "years": "1898–1958"},
    "WAR":  {"full_name": "Western Australian Reports", "brackets": "round", "court": "WASC", "years": "1958–"},

    # === SUBJECT-SPECIFIC UNAUTHORISED ===
    "A Crim R":  {"full_name": "Australian Criminal Reports", "brackets": "round", "court": "various", "years": "1979–"},
    "ACSR":      {"full_name": "Australian Corporations and Securities Reports", "brackets": "round", "court": "various", "years": "1990–"},
    "Fam LR":    {"full_name": "Family Law Reports", "brackets": "round", "court": "FamCA", "years": "1976–"},
    "FLC":       {"full_name": "Family Law Cases", "brackets": "square", "court": "FamCA", "years": "1976–"},
    "IR":        {"full_name": "Industrial Reports", "brackets": "round", "court": "various", "years": "1972–"},
    "IPR":       {"full_name": "Intellectual Property Reports", "brackets": "round", "court": "various", "years": "1975–"},
    "LGERA":     {"full_name": "Local Government and Environment Reports of Australia", "brackets": "round", "court": "various", "years": "1978–"},
    "MVR":       {"full_name": "Motor Vehicle Reports", "brackets": "round", "court": "various", "years": ""},

    # === ENGLISH REPORTS (commonly cited in Australian law) ===
    "AC":       {"full_name": "Appeal Cases", "brackets": "round", "court": "UKHL/UKSC", "years": "1891–"},
    "QB":       {"full_name": "Queen's Bench", "brackets": "round", "court": "EWHC", "years": ""},
    "KB":       {"full_name": "King's Bench", "brackets": "round", "court": "EWHC", "years": ""},
    "Ch":       {"full_name": "Chancery", "brackets": "round", "court": "EWHC", "years": ""},
    "All ER":   {"full_name": "All England Law Reports", "brackets": "round", "court": "various", "years": "1936–"},
    "WLR":      {"full_name": "Weekly Law Reports", "brackets": "round", "court": "various", "years": "1953–"},
}


# Medium-neutral court identifiers — ALL use SQUARE brackets for year
# Source: AGLC4 s 2.3.1, pages 54–55
COURT_IDENTIFIERS: dict[str, dict] = {
    # === COMMONWEALTH ===
    "HCA":     {"full_name": "High Court of Australia", "brackets": "square", "years": "1998–"},
    "HCASL":   {"full_name": "High Court of Australia — Special Leave Dispositions", "brackets": "square", "years": "2008–"},
    "FCA":     {"full_name": "Federal Court of Australia", "brackets": "square", "years": "1999–"},
    "FCAFC":   {"full_name": "Federal Court of Australia — Full Court", "brackets": "square", "years": "2002–"},
    "FamCA":   {"full_name": "Family Court of Australia", "brackets": "square", "years": "1998–"},
    "FamCAFC": {"full_name": "Family Court of Australia — Full Court", "brackets": "square", "years": "2008–"},
    "FCCA":    {"full_name": "Federal Circuit Court of Australia", "brackets": "square", "years": "2013–"},
    "FedCFamC2F": {"full_name": "Federal Circuit and Family Court (Div 2)", "brackets": "square", "years": "2021–"},
    "AATA":    {"full_name": "Administrative Appeals Tribunal", "brackets": "square", "years": ""},

    # === ACT ===
    "ACTSC":   {"full_name": "Supreme Court of the ACT", "brackets": "square", "years": "1998–"},
    "ACTCA":   {"full_name": "ACT Court of Appeal", "brackets": "square", "years": "2002–"},

    # === NSW ===
    "NSWSC":   {"full_name": "Supreme Court of New South Wales", "brackets": "square", "years": "1999–"},
    "NSWCA":   {"full_name": "New South Wales Court of Appeal", "brackets": "square", "years": "1999–"},
    "NSWCCA":  {"full_name": "New South Wales Court of Criminal Appeal", "brackets": "square", "years": "1999–"},
    "NSWDC":   {"full_name": "District Court of New South Wales", "brackets": "square", "years": ""},
    "NSWLEC":  {"full_name": "Land and Environment Court of NSW", "brackets": "square", "years": ""},

    # === NT ===
    "NTSC":    {"full_name": "Supreme Court of the Northern Territory", "brackets": "square", "years": "1999–"},
    "NTCA":    {"full_name": "Northern Territory Court of Appeal", "brackets": "square", "years": "2000–"},
    "NTCCA":   {"full_name": "Northern Territory Court of Criminal Appeal", "brackets": "square", "years": "2000–"},

    # === QLD ===
    "QSC":     {"full_name": "Supreme Court of Queensland", "brackets": "square", "years": "1998–"},
    "QCA":     {"full_name": "Queensland Court of Appeal", "brackets": "square", "years": "1998–"},
    "QDC":     {"full_name": "District Court of Queensland", "brackets": "square", "years": ""},

    # === SA ===
    "SASC":    {"full_name": "Supreme Court of South Australia", "brackets": "square", "years": "1999–"},
    "SASCFC":  {"full_name": "Supreme Court of SA — Full Court", "brackets": "square", "years": "2010–"},
    "SADC":    {"full_name": "District Court of South Australia", "brackets": "square", "years": ""},
    "SAET":    {"full_name": "South Australian Employment Tribunal", "brackets": "square", "years": ""},

    # === TAS ===
    "TASSC":   {"full_name": "Supreme Court of Tasmania", "brackets": "square", "years": "1999–"},
    "TASCCA":  {"full_name": "Tasmanian Court of Criminal Appeal", "brackets": "square", "years": "2010–"},
    "TASFC":   {"full_name": "Supreme Court of Tasmania — Full Court", "brackets": "square", "years": "2010–"},
    "TASCC":   {"full_name": "Tasmanian County Court", "brackets": "square", "years": ""},

    # === VIC ===
    "VSC":     {"full_name": "Supreme Court of Victoria", "brackets": "square", "years": "1998–"},
    "VSCA":    {"full_name": "Victorian Court of Appeal", "brackets": "square", "years": "1998–"},
    "VCC":     {"full_name": "County Court of Victoria", "brackets": "square", "years": ""},

    # === WA ===
    "WASC":    {"full_name": "Supreme Court of Western Australia", "brackets": "square", "years": "1999–"},
    "WASCA":   {"full_name": "WA Court of Appeal", "brackets": "square", "years": "1999–"},
    "WADC":    {"full_name": "District Court of Western Australia", "brackets": "square", "years": ""},
    "WAMW":    {"full_name": "WA Mining Warden", "brackets": "square", "years": ""},
    "WASAT":   {"full_name": "State Administrative Tribunal of WA", "brackets": "square", "years": ""},

    # === NZ (commonly cited) ===
    "NZSC":    {"full_name": "Supreme Court of New Zealand", "brackets": "square", "years": "2004–"},
    "NZCA":    {"full_name": "New Zealand Court of Appeal", "brackets": "square", "years": ""},
    "NZHC":    {"full_name": "New Zealand High Court", "brackets": "square", "years": ""},

    # === UK (commonly cited) ===
    "UKSC":    {"full_name": "United Kingdom Supreme Court", "brackets": "square", "years": "2009–"},
    "UKHL":    {"full_name": "United Kingdom House of Lords", "brackets": "square", "years": "2001–09"},
    "UKPC":    {"full_name": "United Kingdom Privy Council", "brackets": "square", "years": ""},
    "EWCA":    {"full_name": "England and Wales Court of Appeal", "brackets": "square", "years": "2001–"},
    "EWHC":    {"full_name": "England and Wales High Court", "brackets": "square", "years": "2001–"},
}


# =============================================================================
# QUICK LOOKUP: get bracket type for any identifier
# =============================================================================

def get_bracket_type(identifier: str) -> str | None:
    """Return 'round' or 'square' for a report series or court identifier.

    Args:
        identifier: e.g., "CLR", "HCA", "NSWLR", "WASC"

    Returns:
        "round" or "square", or None if not found.
    """
    if identifier in COURT_IDENTIFIERS:
        return COURT_IDENTIFIERS[identifier]["brackets"]
    if identifier in REPORT_SERIES:
        return REPORT_SERIES[identifier]["brackets"]
    return None


def is_medium_neutral(identifier: str) -> bool:
    """Check if an identifier is a medium-neutral court identifier (always square brackets)."""
    return identifier in COURT_IDENTIFIERS


def all_round_bracket_series() -> set[str]:
    """Return all report series that use round brackets."""
    return {k for k, v in REPORT_SERIES.items() if v["brackets"] == "round"}


def all_square_bracket_identifiers() -> set[str]:
    """Return all identifiers that use square brackets (all MNC + FLC)."""
    result = set(COURT_IDENTIFIERS.keys())
    result.update(k for k, v in REPORT_SERIES.items() if v["brackets"] == "square")
    return result


# =============================================================================
# JURISDICTION ABBREVIATIONS
# Source: AGLC4 s 3.1
# =============================================================================

JURISDICTIONS: dict[str, str] = {
    # Abbreviation → Full name
    "Cth":  "Commonwealth",
    "NSW":  "New South Wales",
    "Vic":  "Victoria",
    "Qld":  "Queensland",
    "WA":   "Western Australia",
    "SA":   "South Australia",
    "Tas":  "Tasmania",
    "ACT":  "Australian Capital Territory",
    "NT":   "Northern Territory",
    "NZ":   "New Zealand",
    "UK":   "United Kingdom",
}

# Reverse lookup: full name → abbreviation
JURISDICTION_FULL_TO_ABBR: dict[str, str] = {
    "Commonwealth": "Cth",
    "New South Wales": "NSW",
    "Victoria": "Vic",
    "Queensland": "Qld",
    "Western Australia": "WA",
    "South Australia": "SA",
    "Tasmania": "Tas",
    "Australian Capital Territory": "ACT",
    "Northern Territory": "NT",
    "New Zealand": "NZ",
    "United Kingdom": "UK",
}


# =============================================================================
# PINPOINT ABBREVIATIONS
# Source: AGLC4 s 3.2, pages 69–70
# =============================================================================

PINPOINT_ABBREVIATIONS: dict[str, dict[str, str]] = {
    # Full word → {"singular": abbr, "plural": abbr}
    "Appendix":      {"singular": "app", "plural": "apps"},
    "Article":       {"singular": "art", "plural": "arts"},
    "Chapter":       {"singular": "ch", "plural": "chs"},
    "Clause":        {"singular": "cl", "plural": "cls"},
    "Division":      {"singular": "div", "plural": "divs"},
    "Paragraph":     {"singular": "para", "plural": "paras"},
    "Part":          {"singular": "pt", "plural": "pts"},
    "Schedule":      {"singular": "sch", "plural": "schs"},
    "Section":       {"singular": "s", "plural": "ss"},
    "Sub-clause":    {"singular": "sub-cl", "plural": "sub-cls"},
    "Subdivision":   {"singular": "sub-div", "plural": "sub-divs"},
    "Sub-paragraph": {"singular": "sub-para", "plural": "sub-paras"},
    "Subsection":    {"singular": "sub-s", "plural": "sub-ss"},
    "Regulation":    {"singular": "reg", "plural": "regs"},
    "Rule":          {"singular": "r", "plural": "rr"},
}

# Quick lookup: wrong form → correct form (for validation)
PINPOINT_CORRECTIONS: dict[str, str] = {
    "section": "s",
    "Section": "s",
    "sec": "s",
    "sec.": "s",
    "§": "s",
    "sections": "ss",
    "Sections": "ss",
    "regulation": "reg",
    "Regulation": "reg",
    "regulations": "regs",
    "Regulations": "regs",
    "rule": "r",
    "Rule": "r",
    "rules": "rr",
    "Rules": "rr",
    "clause": "cl",
    "Clause": "cl",
    "clauses": "cls",
    "Clauses": "cls",
    "schedule": "sch",
    "Schedule": "sch",
    "schedules": "schs",
    "part": "pt",
    "Part": "pt",
    "parts": "pts",
    "division": "div",
    "Division": "div",
    "divisions": "divs",
    "paragraph": "para",
    "Paragraph": "para",
    "paragraphs": "paras",
    "chapter": "ch",
    "Chapter": "ch",
    "chapters": "chs",
    "edition": "ed",
    "Edition": "ed",
    "edn": "ed",
    "edn.": "ed",
}


# =============================================================================
# COMMONLY CITED AUSTRALIAN JOURNAL NAMES
# AGLC4 requires FULL journal names (not abbreviated) — this maps abbreviations → full
# Source: AGLC4 s 5.1, Appendix A
# =============================================================================

JOURNAL_ABBREVIATIONS: dict[str, str] = {
    # Abbreviation → Full name (for expansion)
    "UNSWLJ":    "University of New South Wales Law Journal",
    "UQLJ":      "University of Queensland Law Journal",
    "UWALR":     "University of Western Australia Law Review",
    "Mon LR":    "Monash University Law Review",
    "Mon ULR":   "Monash University Law Review",
    "Melb ULR":  "Melbourne University Law Review",
    "Melb Uni L Rev": "Melbourne University Law Review",
    "MULR":      "Melbourne University Law Review",
    "Syd LR":    "Sydney Law Review",
    "SydLR":     "Sydney Law Review",
    "SYDLR":     "Sydney Law Review",
    "Adel LR":   "Adelaide Law Review",
    "ALJ":       "Australian Law Journal",
    "AJCL":      "Australian Journal of Corporate Law",
    "ALMD":      "Australian Law and Management Digest",
    "ABLR":      "Australian Business Law Review",
    "AJLL":      "Australian Journal of Labour Law",
    "AIPJ":      "Australian Intellectual Property Journal",
    "CLJ":       "Cambridge Law Journal",
    "LQR":       "Law Quarterly Review",
    "MLR":       "Modern Law Review",
    "OJLS":      "Oxford Journal of Legal Studies",
    "PLR":       "Public Law Review",
    "UNSW LJ":   "University of New South Wales Law Journal",
    "Fed LR":    "Federal Law Review",
    "Fed L Rev":  "Federal Law Review",
    "FedLR":     "Federal Law Review",
    "UTAS LR":   "University of Tasmania Law Review",
    "JCL":       "Journal of Contract Law",
    "Crim LJ":   "Criminal Law Journal",
    "AJFL":      "Australian Journal of Family Law",
    "AULR":      "Australian University Law Review",
    "QUT LR":    "Queensland University of Technology Law Review",
    "QUTLR":     "Queensland University of Technology Law Review",
    "Griff LR":  "Griffith Law Review",
    "JCULR":     "James Cook University Law Review",
    "Deakin LR": "Deakin Law Review",
    "Alt LJ":    "Alternative Law Journal",
    "AILR":      "Australian Indigenous Law Reporter",
    "AILREV":    "Australian Indigenous Law Review",
    "JAAL":      "Journal of Australian Taxation",
    "CompLJ":    "Competition Law Journal",
    "EPLJ":      "Environmental and Planning Law Journal",
    "APLJ":      "Asia Pacific Law Journal",
    "Res Judicatae": "Res Judicatae",
    "LSWA Brief": "Brief (Law Society of Western Australia)",
}


# =============================================================================
# WRONG CITATION STYLE INDICATORS
# Detect when students use Bluebook, OSCOLA, APA, Chicago, or Harvard
# =============================================================================

WRONG_STYLE_INDICATORS: dict[str, str] = {
    "v.":       "bluebook",       # Bluebook uses "v." with period
    "C.L.R.":   "bluebook",       # Bluebook abbreviates with periods
    "F.C.R.":   "bluebook",       # Bluebook abbreviates with periods
    "H.C.A.":   "bluebook",       # Bluebook abbreviates with periods
    "Id.":      "bluebook",       # Bluebook short form for Ibid
    "Id.,":     "bluebook",
    "supra":    "bluebook",       # Bluebook subsequent reference
    "supra note": "bluebook",
    "infra":    "bluebook",       # Bluebook forward reference
    "op cit":   "oxford",         # Oxford/traditional style
    "loc cit":  "oxford",
    "above n":  "nz_style",       # NZ Law Style Guide format
    "(note ":   "non_standard",   # Wrong subsequent reference format
    "https://doi.org": "apa",     # APA includes DOIs
    "Retrieved from": "apa",      # APA access phrase
    "Available at": "non_standard",
    "accessed on": "non_standard",
}


# =============================================================================
# SPECIAL CASE: Australian Constitution
# AGLC4: cite as "Australian Constitution" — no jurisdiction, no year
# =============================================================================

CONSTITUTION_VARIANTS: dict[str, str] = {
    # Wrong forms → correct form
    "Commonwealth of Australia Constitution Act 1900": "Australian Constitution",
    "Constitution of the Commonwealth of Australia": "Australian Constitution",
    "Australian Constitution Act": "Australian Constitution",
    "The Constitution": "Australian Constitution",
    "Commonwealth Constitution": "Australian Constitution",
}
