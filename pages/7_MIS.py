from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from utils.constants import (
    ATTENDANCE_HEADERS,
    ATTENDANCE_TAB,
    DAILY_REPORTS_HEADERS,
    DAILY_REPORTS_TAB,
    EMPLOYEES_HEADERS,
    EMPLOYEES_TAB,
    EMPLOYEE_TASKS_HEADERS,
    EMPLOYEE_TASKS_TAB,
)
from utils.sheets_db import append_record, get_or_create_worksheet, read_records, update_record
from utils.ui import admin_login_widget, check_admin_access, get_spreadsheet_connection, init_page
from utils.whatsapp_sender import send_whatsapp_message


def to_float(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def to_int(value):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0


def parse_date(value):
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def parse_time(value):
    try:
        return datetime.strptime(str(value).strip(), "%H:%M:%S").time()
    except (TypeError, ValueError):
        return None


def calculate_hours(time_in_str, time_out_str):
    if not time_in_str or not time_out_str:
        return ""
    try:
        t_in = datetime.strptime(time_in_str, "%H:%M:%S")
        t_out = datetime.strptime(time_out_str, "%H:%M:%S")
        if t_out < t_in:
            t_out = t_out + timedelta(days=1)
        delta = t_out - t_in
        hours = delta.total_seconds() / 3600
        return f"{hours:.2f}"
    except:
        return ""


def get_attendance_status(hours_str):
    if not hours_str:
        return ""
    try:
        hours = float(hours_str)
        if hours >= 5:
            return "Present"
        else:
            return "Half Day"
    except:
        return ""


init_page("MIS System")
st.title("Management Information System")
admin_login_widget()

spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

employees_ws = get_or_create_worksheet(spreadsheet, EMPLOYEES_TAB, EMPLOYEES_HEADERS)
tasks_ws = get_or_create_worksheet(spreadsheet, EMPLOYEE_TASKS_TAB, EMPLOYEE_TASKS_HEADERS)
reports_ws = get_or_create_worksheet(spreadsheet, DAILY_REPORTS_TAB, DAILY_REPORTS_HEADERS)
attendance_ws = get_or_create_worksheet(spreadsheet, ATTENDANCE_TAB, ATTENDANCE_HEADERS)

employees = read_records(employees_ws, EMPLOYEES_HEADERS)
tasks = read_records(tasks_ws, EMPLOYEE_TASKS_HEADERS)
reports = read_records(reports_ws, DAILY_REPORTS_HEADERS)
attendance_records = read_records(attendance_ws, ATTENDANCE_HEADERS)

section = st.radio(
    "Select Section",
    options=["Employee Report Form", "Admin Panel", "Admin Dashboard"],
    horizontal=True,
)

if section == "Employee Report Form":
    st.subheader("Mark Attendance")

    if not employees:
        st.info("No employees found. Admin needs to add employees first.")
        st.stop()

    employee_names = [e.get("Name", "").strip() for e in employees if e.get("Name", "").strip()]
    selected_employee = st.selectbox("Select Your Name", employee_names, key="report_emp")
    attendance_date = date.today()

    today_attendance = next(
        (r for r in attendance_records if r.get("Employee Name", "").strip() == selected_employee and parse_date(r.get("Date", "")) == attendance_date),
        None,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🟢 Time In", key="time_in_btn", use_container_width=True):
            current_time = datetime.now().strftime("%H:%M:%S")
            if today_attendance:
                st.info(f"Attendance record already exists for {selected_employee} today.")
            else:
                append_record(
                    attendance_ws,
                    ATTENDANCE_HEADERS,
                    {
                        "Date": attendance_date.isoformat(),
                        "Employee Name": selected_employee,
                        "Time In": current_time,
                        "Time Out": "",
                        "Total Hours": "",
                        "Status": "",
                    },
                )
                time_display = datetime.strptime(current_time, "%H:%M:%S").strftime("%I:%M %p")
                st.success(f"Time In recorded at {time_display}")
                st.rerun()

    with col2:
        if st.button("🔴 Time Out", key="time_out_btn", use_container_width=True):
            current_time = datetime.now().strftime("%H:%M:%S")
            if not today_attendance:
                st.error("Please mark Time In first.")
            else:
                time_in = today_attendance.get("Time In", "").strip()
                if not time_in:
                    st.error("No Time In recorded for today.")
                else:
                    total_hours = calculate_hours(time_in, current_time)
                    status = get_attendance_status(total_hours)
                    update_record(
                        attendance_ws,
                        today_attendance["_row"],
                        ATTENDANCE_HEADERS,
                        {
                            "Date": attendance_date.isoformat(),
                            "Employee Name": selected_employee,
                            "Time In": time_in,
                            "Time Out": current_time,
                            "Total Hours": total_hours,
                            "Status": status,
                        },
                    )
                    time_display = datetime.strptime(current_time, "%H:%M:%S").strftime("%I:%M %p")
                    st.success(f"Time Out recorded at {time_display}")
                    st.rerun()

    if today_attendance:
        st.markdown("---")
        st.info(
            f"**Attendance Summary**: Time In: {today_attendance.get('Time In', 'Not marked')} | "
            f"Time Out: {today_attendance.get('Time Out', 'Not marked')} | "
            f"Total Hours: {today_attendance.get('Total Hours', '—')} | "
            f"Status: {today_attendance.get('Status', '—')}"
        )

    st.markdown("---")
    st.subheader("Daily Report Submission")

    report_date = st.date_input("Report Date", value=date.today())

    with st.form("daily_report_form", clear_on_submit=True):
        tasks_completed = st.text_area("Tasks Completed")
        orders_dispatched = st.number_input("Orders Dispatched", min_value=0, step=1, value=0)
        payments_collected = st.number_input("Payments Collected (₹)", min_value=0.0, step=0.01, value=0.0)
        expenses_incurred = st.number_input("Expenses Incurred (₹)", min_value=0.0, step=0.01, value=0.0)
        issues_remarks = st.text_area("Issues / Remarks")

        submit_report = st.form_submit_button("Submit Report", type="primary")
        if submit_report:
            try:
                append_record(
                    reports_ws,
                    DAILY_REPORTS_HEADERS,
                    {
                        "Date": report_date.isoformat(),
                        "Employee Name": selected_employee,
                        "Tasks Completed": tasks_completed.strip(),
                        "Orders Dispatched": str(int(orders_dispatched)),
                        "Payments Collected": f"{float(payments_collected):.2f}",
                        "Expenses Incurred": f"{float(expenses_incurred):.2f}",
                        "Issues/Remarks": issues_remarks.strip(),
                    },
                )
                st.success("Report submitted successfully!")
            except Exception as exc:
                st.error(f"Error submitting report: {exc}")

elif section == "Admin Panel":
    st.subheader("Admin Panel - Password Required")

    password_input = st.text_input("Enter Password", type="password")
    if password_input != "National1975":
        st.warning("Please enter the correct password to access the Admin Panel.")
        st.stop()

    admin_tab_1, admin_tab_2, admin_tab_3 = st.tabs(["Manage Employees", "Assign Tasks", "Attendance Management"])

    with admin_tab_1:
        st.markdown("### Add New Employee")
        if check_admin_access():
            with st.form("add_employee_form", clear_on_submit=True):
                emp_name = st.text_input("Employee Name")
                emp_role = st.selectbox("Role", ["Warehouse", "Dispatch", "Admin"])
                emp_phone = st.text_input("Phone Number (with country code, e.g. +919876543210)")
                emp_whatsapp = st.text_input("WhatsApp Number (with country code, e.g. +919876543210)")

                emp_submit = st.form_submit_button("Add Employee", type="primary")
                if emp_submit:
                    if not emp_name.strip():
                        st.error("Employee name is required.")
                    elif not emp_phone.strip():
                        st.error("Phone number is required.")
                    else:
                        try:
                            append_record(
                                employees_ws,
                                EMPLOYEES_HEADERS,
                                {
                                    "Name": emp_name.strip(),
                                    "Role": emp_role,
                                    "Phone": emp_phone.strip(),
                                    "WhatsApp": emp_whatsapp.strip(),
                                    "Date Added": date.today().isoformat(),
                                },
                            )
                            st.success(f"Employee {emp_name} added successfully!")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Error adding employee: {exc}")
        else:
            st.warning("🔐 Admin login required to edit or delete records.")

        st.markdown(f"### Current Employees ({len(employees)} total)")
        if employees:
            with st.expander(f"📋 View All Employees ({len(employees)} records) — click to expand", expanded=False):
                emp_df = pd.DataFrame(employees).drop(columns=["_row"])
                st.dataframe(emp_df, use_container_width=True, hide_index=True)
        else:
            st.info("No employees added yet.")

    with admin_tab_2:
        st.markdown("### Assign Daily Task")

        if not employees:
            st.info("No employees found. Add employees first.")
            st.stop()

        employee_names = [e.get("Name", "").strip() for e in employees if e.get("Name", "").strip()]
        employee_map = {e.get("Name", "").strip(): e for e in employees}

        with st.form("assign_task_form", clear_on_submit=True):
            task_date = st.date_input("Task Date", value=date.today())
            selected_emp = st.selectbox("Select Employee", employee_names, key="task_emp")
            task_description = st.text_area("Task Description")
            task_target = st.text_input("Target (e.g., 'Dispatch 5 orders')")

            task_submit = st.form_submit_button("Send Task on WhatsApp", type="primary")
            if task_submit:
                if not task_description.strip() or not task_target.strip():
                    st.error("Task and Target are required.")
                else:
                    emp = employee_map.get(selected_emp)
                    emp_whatsapp = emp.get("WhatsApp", "").strip() if emp else ""

                    if not emp_whatsapp:
                        st.error("Employee does not have a WhatsApp number.")
                    else:
                        message = (
                            f"Good morning {selected_emp}!\n\n"
                            f"Your tasks for today {task_date.strftime('%Y-%m-%d')}:\n"
                            f"{task_description}\n\n"
                            f"Target: {task_target}\n\n"
                            "Please submit your end-of-day report by 7 PM.\n"
                            "- Satyam Machinery Parts"
                        )

                        success, msg = send_whatsapp_message(emp_whatsapp, message, wait_time=30)
                        if success:
                            st.success(msg)
                            try:
                                append_record(
                                    tasks_ws,
                                    EMPLOYEE_TASKS_HEADERS,
                                    {
                                        "Date": task_date.isoformat(),
                                        "Employee Name": selected_emp,
                                        "Task": task_description.strip(),
                                        "Target": task_target.strip(),
                                        "Status": "Assigned",
                                        "Report Submitted": "No",
                                    },
                                )
                                st.success("Task saved to database!")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Error saving task: {exc}")
                        else:
                            st.error(msg)

        st.markdown("### Today's Task Assignments")
        today_tasks = [t for t in tasks if parse_date(t.get("Date", "")) == date.today()]
        st.markdown(f"**{len(today_tasks)} tasks assigned today**")
        if today_tasks:
            with st.expander(f"📋 View Tasks ({len(today_tasks)} records) — click to expand", expanded=False):
                tasks_df = pd.DataFrame(today_tasks).drop(columns=["_row"])
                st.dataframe(tasks_df, use_container_width=True, hide_index=True)
        else:
            st.info("No tasks assigned for today.")

    with admin_tab_3:
        st.markdown("### Attendance Management")
        today_attendance_records = [r for r in attendance_records if parse_date(r.get("Date", "")) == date.today()]

        attendance_summary = {}
        for emp in employees:
            emp_name = emp.get("Name", "").strip()
            emp_att = next((r for r in today_attendance_records if r.get("Employee Name", "").strip() == emp_name), None)
            if emp_att:
                attendance_summary[emp_name] = emp_att
            else:
                attendance_summary[emp_name] = {
                    "Date": date.today().isoformat(),
                    "Employee Name": emp_name,
                    "Time In": "Not marked",
                    "Time Out": "Not marked",
                    "Total Hours": "",
                    "Status": "Absent",
                }

        st.markdown(f"### Today's Attendance ({len(today_attendance_records)} checked in)")
        if today_attendance_records:
            with st.expander(f"📋 View Attendance ({len(today_attendance_records)} records) — click to expand", expanded=False):
                att_df = pd.DataFrame(today_attendance_records).drop(columns=["_row"])
                st.dataframe(att_df, use_container_width=True, hide_index=True)
        else:
            st.info("No attendance recorded yet today.")

        st.markdown(f"### All Employees Summary ({len(employees)} total)")
        summary_rows = []
        for emp_name, att_rec in sorted(attendance_summary.items()):
            summary_rows.append({
                "Employee": emp_name,
                "Time In": att_rec.get("Time In", "Not marked"),
                "Time Out": att_rec.get("Time Out", "Not marked"),
                "Total Hours": att_rec.get("Total Hours", "—"),
                "Status": att_rec.get("Status", "Absent"),
            })
        
        with st.expander(f"📋 View Summary ({len(summary_rows)} records) — click to expand", expanded=False):
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

elif section == "Admin Dashboard":
    st.subheader("Admin Performance Dashboard - Password Required")

    password_input = st.text_input("Enter Password", type="password", key="dashboard_pwd")
    if password_input != "National1975":
        st.warning("Please enter the correct password to access the Dashboard.")
        st.stop()

    selected_report_date = st.date_input("Select Date for Reports", value=date.today())

    day_reports = [r for r in reports if parse_date(r.get("Date", "")) == selected_report_date]
    day_attendance = [r for r in attendance_records if parse_date(r.get("Date", "")) == selected_report_date]

    st.markdown("---")

    attendance_present = sum(1 for r in day_attendance if r.get("Status", "").strip() == "Present")
    total_employees = len(employees)
    st.markdown(f"### Attendance: :green[{attendance_present}/{total_employees} employees present today]")

    col1, col2, col3, col4 = st.columns(4)
    present_count = sum(1 for r in day_attendance if r.get("Status", "").strip() == "Present")
    half_day_count = sum(1 for r in day_attendance if r.get("Status", "").strip() == "Half Day")
    absent_count = total_employees - present_count - half_day_count

    col1.metric("Present", present_count)
    col2.metric("Half Day", half_day_count)
    col3.metric("Absent", absent_count)

    st.markdown("---")
    st.markdown(f"### Performance Reports for {selected_report_date.strftime('%d %b %Y')}")

    if day_reports:
        col1, col2, col3 = st.columns(3)
        total_dispatches = sum(to_int(r.get("Orders Dispatched", 0)) for r in day_reports)
        total_payments = sum(to_float(r.get("Payments Collected", 0)) for r in day_reports)
        total_expenses = sum(to_float(r.get("Expenses Incurred", 0)) for r in day_reports)

        col1.metric("Total Orders Dispatched", total_dispatches)
        col2.metric("Total Payments Collected", f"₹{total_payments:,.2f}")
        col3.metric("Total Expenses", f"₹{total_expenses:,.2f}")

        st.markdown("---")
        st.markdown(f"### Employee Reports ({len(day_reports)} submitted)")
        with st.expander(f"📋 View All Reports ({len(day_reports)} records) — click to expand", expanded=False):
            reports_df = pd.DataFrame(day_reports).drop(columns=["_row"])
            st.dataframe(reports_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### vs Target Comparison")
        day_tasks = [t for t in tasks if parse_date(t.get("Date", "")) == selected_report_date]

        if day_tasks:
            comparison_rows = []
            for report in day_reports:
                emp_name = report.get("Employee Name", "").strip()
                emp_task = next((t for t in day_tasks if t.get("Employee Name", "").strip() == emp_name), None)

                if emp_task:
                    target = emp_task.get("Target", "").strip()
                    dispatched = to_int(report.get("Orders Dispatched", 0))
                    comparison_rows.append({
                        "Employee": emp_name,
                        "Target": target,
                        "Orders Dispatched": dispatched,
                        "Status": "✓ On Track" if dispatched > 0 else "⚠ No Progress",
                    })

            if comparison_rows:
                with st.expander(f"📋 View Comparison ({len(comparison_rows)} records) — click to expand", expanded=False):
                    st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)

        st.markdown("---")
        reports_df = pd.DataFrame(day_reports).drop(columns=["_row"])
        csv_data = reports_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Reports as CSV",
            data=csv_data,
            file_name=f"daily_reports_{selected_report_date.isoformat()}.csv",
            mime="text/csv",
        )
    else:
        st.info(f"No reports submitted for {selected_report_date.strftime('%d %b %Y')}.")
