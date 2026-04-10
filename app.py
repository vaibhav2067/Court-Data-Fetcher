from datetime import datetime
import json
import sqlite3

from flask import Flask, render_template, request

import db
from selenium_worker import get_captcha, reload_captcha, submit_form

app = Flask(__name__)
db.init_db()

CASE_TYPES = [
    "ADMIN.REPORT", "ARB.A.", "ARB. A. (COMM.)", "ARB.P.", "BAIL APPLN.", "CA",
    "CA (COMM.IPD-CR)", "C.A.(COMM.IPD-GI)", "C.A.(COMM.IPD-PAT)", "C.A.(COMM.IPD-PV)",
    "C.A.(COMM.IPD-TM)", "CAVEAT(CO.)", "CC(ARB.)", "CCP(CO.)", "CCP(REF)", "CEAC",
    "CEAR", "CHAT.A.C.", "CHAT.A.REF", "CMI", "CM(M)", "CM(M)-IPD", "C.O.", "CO.APP.",
    "CO.APPL.(C)", "CO.APPL.(M)", "CO.A(SB)", "C.O.(COMM.IPD-CR)", "C.O.(COMM.IPD-GI)",
    "C.O.(COMM.IPD-PAT)", "C.O. (COMM.IPD-TM)", "CO.EX.", "CONT.APP.(C)", "CONT.CAS(C)",
    "CONT.CAS.(CRL)", "CO.PET.", "C.REF.(O)", "CRL.A.", "CRL.L.P.", "CRL.M.C.",
    "CRL.M.(CO.)", "CRL.M.I.", "CRL.O.", "CRL.O.(CO.)", "CRL.REF.", "CRL.REV.P.",
    "CRL.REV.P.(MAT.)", "CRL.REV.P.(NDPS)", "CRL.REV.P.(NI)", "C.R.P.", "CRP-IPD",
    "C.RULE", "CS(COMM)", "CS(OS)", "CS(OS) GP", "CUSAA", "CUS.A.C.", "CUS.A.R.",
    "CUSTOM A.", "DEATH SENTENCE REF.", "DEMO", "EDC", "EDR", "EFA(COMM)", "EFA(OS)",
    "EFA(OS)  (COMM)", "EFA(OS)(IPD)", "EL.PET.", "ETR", "EX.F.A.", "EX.P.", "EX.S.A.",
    "FAO", "FAO (COMM)", "FAO-IPD", "FAO(OS)", "FAO(OS) (COMM)", "FAO(OS)(IPD)", "GCAC",
    "GCAR", "GTA", "GTC", "GTR", "I.A.", "I.P.A.", "ITA", "ITC", "ITR", "ITSA",
    "LA.APP.", "LPA", "MAC.APP.", "MAT.", "MAT.APP.", "MAT.APP.(F.C.)", "MAT.CASE",
    "MAT.REF.", "MISC. APPEAL (FEMA)", "MISC. APPEAL(PMLA)", "OA", "OCJA", "O.M.P.",
    "O.M.P. (COMM)", "OMP (CONT.)", "O.M.P. (E)", "O.M.P. (E) (COMM.)",
    "O.M.P.(EFA)(COMM.)", "O.M.P. (ENF.)", "OMP (ENF.) (COMM.)", "O.M.P.(I)",
    "O.M.P.(I) (COMM.)", "O.M.P. (J) (COMM.)", "O.M.P. (MISC.)", "O.M.P.(MISC.)(COMM.)",
    "O.M.P.(T)", "O.M.P. (T) (COMM.)", "O.REF.", "RC.REV.", "RC.S.A.", "RERA APPEAL",
    "REVIEW PET.", "RFA", "RFA(COMM)", "RFA-IPD", "RFA(OS)", "RFA(OS)(COMM)",
    "RFA(OS)(IPD)", "RSA", "SCA", "SDR", "SERTA", "ST.APPL.", "STC", "ST.REF.",
    "SUR.T.REF.", "TEST.CAS.", "TR.P.(C)", "TR.P.(C.)", "TR.P.(CRL.)", "VAT APPEAL",
    "W.P.(C)", "W.P.(C)-IPD", "WP(C)(IPD)", "W.P.(CRL)", "WTA", "WTC", "WTR",
]
YEARS = list(range(datetime.now().year, 1950, -1))


def render_dashboard(**context):
    defaults = {
        "case_types": CASE_TYPES,
        "years": YEARS,
        "captcha": "",
        "data": None,
        "raw_html": None,
        "error": None,
        "form_data": {},
    }
    defaults.update(context)
    return render_template("index.html", **defaults)


@app.route('/')
def index():
    try:
        captcha = get_captcha()
        return render_dashboard(captcha=captcha)
    except Exception as exc:
        return render_dashboard(
            error=f"Unable to connect to the Delhi High Court search page right now: {exc}"
        )

@app.route('/reload_captcha')
def reload_captcha_route():
    try:
        return reload_captcha()
    except Exception as exc:
        return f"ERROR: {exc}"

@app.route('/submit', methods=['POST'])
def submit():
    case_type = request.form['case_type']
    case_number = request.form['case_number']
    case_year = request.form['case_year']
    captcha_entered = request.form['captcha_entered']
    
    form_data = {
        "case_type": case_type,
        "case_number": case_number,
        "case_year": case_year,
    }

    conn = sqlite3.connect('case_data.db')
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO requests (case_type, case_number, case_year, captcha_entered) VALUES (?, ?, ?, ?)',
        (case_type, case_number, case_year, captcha_entered),
    )
    request_id = cur.lastrowid
    conn.commit()

    result_data = submit_form(case_type, case_number, case_year, captcha_entered)

    if isinstance(result_data, dict):
        result_str = json.dumps(result_data, ensure_ascii=False)
    else:
        result_str = str(result_data)

    cur.execute(
        'INSERT INTO results (request_id, result_html) VALUES (?, ?)',
        (request_id, result_str),
    )
    conn.commit()
    conn.close()

    try:
        captcha = reload_captcha()
    except Exception:
        captcha = ""

    if isinstance(result_data, dict) and not result_data.get("error"):
        return render_dashboard(
            captcha=captcha,
            data=result_data if result_data.get("case_no") else None,
            raw_html=result_data.get("raw_html"),
            form_data=form_data,
        )

    error_message = result_data.get("error") if isinstance(result_data, dict) else result_str
    return render_dashboard(captcha=captcha, error=error_message, form_data=form_data)

if __name__ == '__main__':
    app.run(debug=True)
