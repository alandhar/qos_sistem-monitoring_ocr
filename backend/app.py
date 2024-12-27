import os
import hashlib
import camelot
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from sqlalchemy.inspection import inspect

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
app.config["UPLOAD_FOLDER"] = 'data/uploaded_files'
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
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"message": "No file part in the request"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400

    if file and file.filename.endswith(".pdf"):
        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"], secure_filename(file.filename)
        )
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)  # Ensure folder exists
        file.save(file_path)

        try:
            # Extract tables from the uploaded PDF using Camelot
            tables = camelot.read_pdf(file_path)

            if len(tables) == 0:
                return jsonify({"message": "No tables found in the PDF file"}), 400

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
                return (
                    jsonify(
                        {
                            "message": "Data already exists in the database. Upload canceled."
                        }
                    ),
                    409,
                )

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

            return (
                jsonify(
                    {
                        "message": "Reports added successfully!",
                        "profile_data": profile,
                        "general": general,
                        "drilling_parameter": drilling_parameter,
                        "afe": serialize_model(afe_data),
                        "personnel_data": serialize_model(personnel_data),
                        "summary_data": serialize_model(summary_data),
                        "time_breakdown": time_breakdown,
                    }
                ),
                201,
            )

        except Exception as e:
            db.session.rollback()
            return jsonify({"message": f"Failed to process the PDF: {str(e)}"}), 500

    return jsonify({"message": "Invalid file type, please upload a PDF file"}), 400

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
