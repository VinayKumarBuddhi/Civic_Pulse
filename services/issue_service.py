"""
Issue Service - Auto-Assignment and Processing

Implements Step 7 (ISSUE_FLOW_IMPLEMENTATION.md):
- Auto-assign verified issues to best matching NGO
- Update Reports and NGO collections
"""

from typing import Optional, Tuple
from bson import ObjectId
from datetime import datetime

from database.models import ReportsModel, NGOModel
from database.database import get_reports_collection, get_ngo_collection
from rag.ngo_matcher import match_issue_to_ngo


def assign_issue_to_ngo(report_id: str, ngo_id: str) -> Tuple[bool, Optional[str]]:
    """
    Assign issue to NGO.
    
    Steps:
    1. Update Reports.assignedTo = [ngo_id]
    2. Update Reports.Status = "assigned"
    3. Update NGO.Issues = [report_id] (append)
    
    Args:
        report_id: Report/Issue ID (string)
        ngo_id: NGO ID (string)
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        reports_collection = get_reports_collection()
        ngo_collection = get_ngo_collection()
        
        if reports_collection is None or ngo_collection is None:
            return False, "Database connection error"
        
        report_obj_id = ObjectId(report_id)
        ngo_obj_id = ObjectId(ngo_id)
        
        # Verify report exists
        report = reports_collection.find_one({"_id": report_obj_id})
        if not report:
            return False, f"Report {report_id} not found"
        
        # Verify NGO exists and is active
        ngo = ngo_collection.find_one({"_id": ngo_obj_id})
        if not ngo:
            return False, f"NGO {ngo_id} not found"
        
        if not ngo.get("isActive", True):
            return False, f"NGO {ngo_id} is not active"
        
        # Step 1 & 2: Update Reports collection
        # Add NGO to assignedTo array (avoid duplicates)
        assigned_to = report.get("assignedTo", [])
        if ngo_obj_id not in assigned_to:
            assigned_to.append(ngo_obj_id)
        
        reports_collection.update_one(
            {"_id": report_obj_id},
            {
                "$set": {
                    "Status": "assigned",
                    "assignedTo": assigned_to,
                    "updated_at": datetime.now()
                }
            }
        )
        
        # Step 3: Update NGO's Issues array
        issues = ngo.get("Issues", [])
        if report_obj_id not in issues:
            issues.append(report_obj_id)
        
        ngo_collection.update_one(
            {"_id": ngo_obj_id},
            {
                "$set": {
                    "Issues": issues,
                    "updated_at": datetime.now()
                }
            }
        )
        
        return True, None
    
    except Exception as e:
        return False, f"Error assigning issue: {str(e)}"


def auto_assign_verified_issue(report_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Automatically match and assign a verified issue to the best NGO.
    
    This function:
    1. Matches the issue to best NGO using RAG
    2. Assigns the issue to that NGO
    3. Updates both Reports and NGO collections
    
    Args:
        report_id: Report/Issue ID (string)
    
    Returns:
        Tuple of (success: bool, ngo_id: Optional[str], error_message: Optional[str])
        - success: True if assignment succeeded
        - ngo_id: ID of assigned NGO (if successful)
        - error_message: Error message (if failed)
    """
    try:
        # Verify report exists and is verified
        report = ReportsModel.find_by_id(report_id)
        if not report:
            return False, None, f"Report {report_id} not found"
        
        current_status = report.get("Status", "not verified")
        if current_status != "verified":
            return False, None, f"Report {report_id} is not verified (status: {current_status})"
        
        # Check if already assigned
        assigned_to = report.get("assignedTo", [])
        if assigned_to:
            # Already assigned, return success with existing NGO
            ngo_id = str(assigned_to[0])
            return True, ngo_id, None
        
        # Match issue to best NGO
        ngo_id = match_issue_to_ngo(report_id)
        
        if not ngo_id:
            return False, None, "No matching NGO found for this issue"
        
        # Assign issue to NGO
        success, error_msg = assign_issue_to_ngo(report_id, ngo_id)
        
        if success:
            return True, ngo_id, None
        else:
            return False, None, error_msg or "Assignment failed"
    
    except Exception as e:
        return False, None, f"Error in auto-assignment: {str(e)}"

