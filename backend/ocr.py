import re
from datetime import datetime


def cleaning_data_geo_dipa_energi(df):
    def cleaning_profile(df):
        extracted_data = df.iloc[1:4, 0].values

        patterns = {
            "operator": r"OPERATOR\s+(.*)\s+CONTRACTOR",
            "contractor": r"CONTRACTOR\s+(.*)\s+REPORT NO",
            "report_no": r"REPORT NO.\s+#\s*(\d+)",
            "well_pad_name": r"WELL/\s*PAD NAME\s+(.*?)\s+FIELD",
            "field": r"FIELD\s+(\w+)",
            "well_type_profile": r"WELL\s*TYPE/\s*PROFILE\s+(.*?)\s+LATITUDE",
            "latitude_longitude": r"LATITUDE/\s*LONGITUDE\s+(.*?)\s+GL",
            "environment": r"ENVIRONTMENT\s+(\w+)",
            "gl_msl_m": r"GL\s+-\s+MSL\s*\(M\)\s*(.*)",
        }

        profile_data = {}

        for key, pattern in patterns.items():
            for line in extracted_data:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    profile_data[key] = match.group(1).strip()
                    break
        if "gl_msl_m" in profile_data:
            profile_data["gl_msl_m"] = re.sub(r"[^\d.]", "", profile_data["gl_msl_m"])
            profile_data["gl_msl_m"] = (
                float(profile_data["gl_msl_m"]) if profile_data["gl_msl_m"] else None
            )

        return profile_data

    def cleaning_general(df):
        start_index = df[
            df.apply(lambda x: x.astype(str).str.contains("GENERAL").any(), axis=1)
        ].index[0]
        end_index = df[
            df.apply(
                lambda x: x.astype(str).str.contains("24 HOURS SUMMARY").any(), axis=1
            )
        ].index[0]
        df_cleaned = df.iloc[start_index + 1 : end_index - 1, 4].reset_index(drop=True)

        patterns = [
            "rig_type_name",
            "rig_power",
            "kb_elevation",
            "midnight_depth",
            "progress",
            "proposed_td",
            "spud_date",
            "release_date",
            "planned_days",
            "days_from_rig_release",
        ]

        result_dict = {patterns[i]: df_cleaned[i] for i in range(len(patterns))}

        return result_dict

    def cleaning_drilling_parameter(df):
        start_index = df[
            df.apply(
                lambda x: x.astype(str).str.contains("DRILLING PARAMETERS").any(),
                axis=1,
            )
        ].index[0]
        end_index = df[
            df.apply(
                lambda x: x.astype(str).str.contains("24 HOURS SUMMARY").any(), axis=1
            )
        ].index[0]
        df_cleaned = df.iloc[start_index + 1 : end_index - 1, 11].reset_index(drop=True)

        patterns = [
            "average_wob_24_hrs",
            "average_rop_24_hrs",
            "average_surface_rpm_dhm",
            "on_off_bottom_torque",
            "flowrate_spp",
            "air_rate",
            "corr_inhib_foam_rate",
            "puw_sow_rotw",
            "total_drilling_time",
            "ton_miles",
        ]

        result_dict = {patterns[i]: df_cleaned[i] for i in range(len(patterns))}

        return result_dict

    def cleaning_afe(df):
        start_index = df[
            df.apply(lambda x: x.astype(str).str.contains("AFE").any(), axis=1)
        ].index[0]
        end_index = df[
            df.apply(
                lambda x: x.astype(str).str.contains("PERSONNEL IN CHARGE").any(),
                axis=1,
            )
        ].index[0]
        df_cleaned = df.iloc[start_index + 1 : end_index, 12].reset_index(drop=True)

        patterns = {
            "afe_number_afe_cost": r"AFE NUMBER / AFE COST\nUSD ([\d,]+\.\d+)",
            "daily_cost": r"DAILY COST\nUSD ([\d,]+\.\d+)",
            "percent_afe_cumulative_cost": r"% AFE / CUMULATIVE COST\n(?:[\d\.]+)%\nUSD ([\d,]+\.\d+)",
            "daily_mud_cost": r"DAILY MUD COST\nUSD ([\d,]+\.\d+)",
            "cumulative_mud_cost": r"CUMULATIVE MUD COST\nUSD ([\d,]+\.\d+)",
        }

        result_dict = {}

        for key, pattern in patterns.items():
            for line in df_cleaned:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    result_dict[key] = match.group(1).strip()
                    break

        return result_dict

    def cleaning_personnel_in_charge(df):
        start_index = df[
            df.apply(
                lambda x: x.astype(str).str.contains("PERSONNEL IN CHARGE").any(),
                axis=1,
            )
        ].index[0]
        end_index = df[
            df.apply(
                lambda x: x.astype(str).str.contains("24 HOURS SUMMARY").any(), axis=1
            )
        ].index[0]
        df_cleaned = df.iloc[start_index + 1 : end_index, 12].reset_index(drop=True)

        patterns = {
            "day_night_drilling_supv": r"(.+?)\s*DAY/ NIGHT DRILLING SUPV\.",
            "drilling_superintendent": r"(.+?)\s*DRILLING SUPERINTENDENT",
            "rig_superintendent": r"RIG SUPERINTENDENT\n(.+)",
            "drilling_engineer": r"DRILLING ENGINEER\n(.+)",
            "hse_supervisor": r"(.+?)\s*HSE SUPERVISOR",
        }

        result_dict = {}

        for key, pattern in patterns.items():
            for line in df_cleaned:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    result_dict[key] = match.group(1).strip()
                    break

        return result_dict

    def cleaning_summary(df):
        start_index = df[
            df.apply(
                lambda x: x.astype(str).str.contains("24 HOURS SUMMARY").any(), axis=1
            )
        ].index[0]
        end_index = df[
            df.apply(lambda x: x.astype(str).str.contains("STATUS").any(), axis=1)
        ].index[0]
        df_cleaned = df.iloc[start_index : end_index + 1, 4].reset_index(drop=True)

        patterns = ["hours_24_summary", "hours_24_forecast", "status"]

        result_dict = {patterns[i]: df_cleaned[i] for i in range(len(patterns))}

        return result_dict

    def cleaning_time_breakdown(df):
        start_index = df[
            df.apply(
                lambda x: x.astype(str).str.contains("START").any()
                & x.astype(str).str.contains("END").any()
                & x.astype(str).str.contains("ELAPSED").any(),
                axis=1,
            )
        ].index[0]
        end_index = df[
            df.apply(
                lambda x: x.astype(str).str.contains("TOTAL HRS").any()
                & x.astype(str).str.contains("24.0").any(),
                axis=1,
            )
        ].index[0]

        df_cleaned = df.iloc[start_index + 1 : end_index].reset_index(drop=True)
        df_cleaned = df_cleaned.iloc[:, :9]

        def convert_time(time_str):
            if time_str == '24:00':
                return 24.0
            time_obj = datetime.strptime(time_str, "%H:%M")
            return time_obj.hour + time_obj.minute / 60.0
        
        result_list = []
        for i in range(len(df_cleaned)):
            start_time = df_cleaned.iloc[i, 0]
            end_time = df_cleaned.iloc[i, 1]
            start_float = convert_time(start_time)
            end_float = convert_time(end_time)

            result_list.append(
                {
                    "start": start_float,
                    "end": end_float,
                    "elapsed": df_cleaned.iloc[i, 2],
                    "depth": df_cleaned.iloc[i, 3],
                    "pt_npt": df_cleaned.iloc[i, 5],
                    "code": df_cleaned.iloc[i, 6],
                    "description": df_cleaned.iloc[i, 7],
                    "operation": df_cleaned.iloc[i, 8],
                }
            )

        return result_list

    profile = cleaning_profile(df)
    general = cleaning_general(df)
    drilling_parameter = cleaning_drilling_parameter(df)
    afe = cleaning_afe(df)
    personnel_in_charge = cleaning_personnel_in_charge(df)
    summary = cleaning_summary(df)
    time_breakdown = cleaning_time_breakdown(df)

    return (
        profile,
        general,
        drilling_parameter,
        afe,
        personnel_in_charge,
        summary,
        time_breakdown,
    )