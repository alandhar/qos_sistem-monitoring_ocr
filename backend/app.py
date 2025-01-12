import os
import hashlib
import camelot
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
# from sqlalchemy.inspection import inspect
from sqlalchemy.sql import text

from database import (
    Profile,
    GeneralData,
    DrillingParameter,
    AFE,
    PersonnelInCharge,
    Summary,
    TimeBreakdown,
    serialize_model,
    db,
)
from ocr import cleaning_data_geo_dipa_energi
from flask_cors import CORS

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = '/Users/macbook/Documents/Mahasiswa/Proyek Akhir/final_project/data/uploaded_files'
app.config["SQLALCHEMY_DATABASE_URI"] = ('postgresql://postgres:7832@localhost:5433/OCR')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
CORS(app)

db.init_app(app)

def calculate_hash(data_dict):
    data_string = "".join(str(value) for value in data_dict.values())
    return hashlib.md5(data_string.encode()).hexdigest()

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()

@app.route("/upload", methods=["POST"])
def upload_pdfs():
    if "files" not in request.files:
        return jsonify({"message": "No file part in the request"}), 400

    files = request.files.getlist("files")  # Get all files from the request
    if not files or all(file.filename == "" for file in files):
        return jsonify({"message": "No files selected"}), 400

    results = []
    for file in files:
        if file and file.filename.endswith(".pdf"):
            try:
                # Process each file
                file_path = os.path.join(
                    app.config["UPLOAD_FOLDER"], secure_filename(file.filename)
                )
                os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)  # Ensure folder exists
                file.save(file_path)

                # Extract tables from the uploaded PDF using Camelot
                tables = camelot.read_pdf(file_path)

                if len(tables) == 0:
                    results.append(
                        {"filename": file.filename, "message": "No tables found"}
                    )
                    continue

                (
                    profile,
                    general,
                    drilling_parameter,
                    afe,
                    personnel_in_charge,
                    summary,
                    time_breakdown,
                ) = cleaning_data_geo_dipa_energi(tables[0].df)

                time_breakdown = {i: entry for i, entry in enumerate(time_breakdown)}

                unique_hash = calculate_hash(profile)
                existing_profile = Profile.query.filter_by(unique_hash=unique_hash).first()
                if existing_profile:
                    results.append(
                        {
                            "filename": file.filename,
                            "message": "Data already exists in the database. Upload canceled.",
                        }
                    )
                    continue

                # Save the extracted data into the database
                profile_data = Profile(**profile, unique_hash=unique_hash)
                db.session.add(profile_data)
                db.session.commit()

                general_data = GeneralData(**general, profile_id=profile_data.id)
                drilling_data = DrillingParameter(
                    **drilling_parameter, profile_id=profile_data.id
                )
                afe_data = AFE(**afe, profile_id=profile_data.id)
                personnel_data = PersonnelInCharge(
                    **personnel_in_charge, profile_id=profile_data.id
                )
                summary_data = Summary(**summary, profile_id=profile_data.id)

                for item in time_breakdown.values():
                    time_breakdown_data = TimeBreakdown(
                        start=item["start"],
                        end=item["end"],
                        elapsed=item["elapsed"],
                        depth=item["depth"],
                        pt_npt=item["pt_npt"],
                        code=item["code"],
                        description=item["description"],
                        operation=item["operation"],
                        profile_id=profile_data.id,  # Link to the profile_id
                    )
                    db.session.add(time_breakdown_data)

                db.session.add(general_data)
                db.session.add(drilling_data)
                db.session.add(afe_data)
                db.session.add(personnel_data)
                db.session.add(summary_data)
                db.session.commit()

                results.append(
                    {"filename": file.filename, "message": "File processed successfully"}
                )

            except Exception as e:
                db.session.rollback()
                results.append(
                    {"filename": file.filename, "message": f"Failed to process: {str(e)}"}
                )
        else:
            results.append(
                {"filename": file.filename, "message": "Invalid file type, not a PDF"}
            )

    return jsonify({"results": results}), 207

@app.route('/time_breakdown', methods=['GET'])
def get_time_breakdown():
    """
    Fetches all records from the time_breakdown table ordered by profile_id and start.
    """
    try:
        # Execute the SQL query
        query = text("""
            SELECT 
                tb.profile_id, 
                tb.start, 
                tb.end, 
                tb.elapsed, 
                tb.depth,
                tb.description, 
                pf.date, 
                pf.well_pad_name
            FROM time_breakdown tb
            INNER JOIN profile pf
            ON tb.profile_id = pf.id
            ORDER BY pf.date, tb.start ASC;
        """)
        result = db.session.execute(query)

        # Convert result to a list of dictionaries
        time_breakdown = [
            dict(row._mapping) for row in result
        ]

        return jsonify(time_breakdown), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/detail', methods=['GET'])
def get_detail_report():
    try:
        # Query 1: Fetch data from profile and related tables
        detail_query = """
            SELECT 
                pf.id,  
                pf.contractor, 
                pf.report_no, 
                pf.field, 
                pf.latitude_longitude,
                afe.afe_number_afe_cost, 
                afe.daily_cost,
                afe.percent_afe_cumulative_cost, 
                afe.daily_mud_cost, 
                afe.cumulative_mud_cost,
                pic.day_night_drilling_supv, 
                pic.drilling_superintendent, 
                pic.rig_superintendent, 
                pic.drilling_engineer, 
                pic.hse_supervisor,
                smr.hours_24_summary
            FROM profile pf
            INNER JOIN afe ON afe.profile_id = pf.id
            INNER JOIN personnel_in_charge pic ON pic.profile_id = pf.id
            INNER JOIN summary smr ON smr.profile_id = pf.id;
        """
        detail_result = db.session.execute(text(detail_query))
        detail = [dict(row._mapping) for row in detail_result]  

        # Query 2: Fetch data from time_breakdown table
        time_query = "SELECT * FROM time_breakdown;"
        time_result = db.session.execute(text(time_query))
        time = [dict(row._mapping) for row in time_result] 

        # Combine the results into a single response
        return jsonify({"detail": detail, "time": time}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
