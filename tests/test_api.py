"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        "Soccer Team": {
            "description": "Join our varsity soccer team and compete in regional tournaments",
            "schedule": "Mondays and Wednesdays, 4:00 PM - 6:00 PM",
            "max_participants": 25,
            "participants": ["alex@mergington.edu", "sarah@mergington.edu"]
        },
        "Swimming Club": {
            "description": "Learn swimming techniques and train for competitions",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
            "max_participants": 15,
            "participants": ["chris@mergington.edu"]
        },
    }
    
    # Reset to original state
    activities.clear()
    activities.update(original_activities)
    
    yield
    
    # Clean up after test
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Test GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Soccer Team" in data
        assert "Swimming Club" in data
        assert data["Soccer Team"]["max_participants"] == 25
    
    def test_activities_have_required_fields(self, client):
        """Test that activities have all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupForActivity:
    """Test POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Soccer Team/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Soccer Team"]["participants"]
    
    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/NonExistent Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_already_registered(self, client):
        """Test signup when student is already registered"""
        # First signup
        client.post("/activities/Soccer Team/signup?email=test@mergington.edu")
        
        # Try to signup again
        response = client.post(
            "/activities/Soccer Team/signup?email=test@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student already signed up for this activity"
    
    def test_signup_with_special_characters(self, client):
        """Test signup with email containing special characters"""
        response = client.post(
            "/activities/Soccer Team/signup?email=john.doe%2Btest@mergington.edu"
        )
        assert response.status_code == 200


class TestRemoveParticipant:
    """Test DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_participant_success(self, client):
        """Test successful removal of a participant"""
        response = client.delete(
            "/activities/Soccer Team/participants/alex@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "alex@mergington.edu" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "alex@mergington.edu" not in activities_data["Soccer Team"]["participants"]
    
    def test_remove_participant_activity_not_found(self, client):
        """Test removal from non-existent activity"""
        response = client.delete(
            "/activities/NonExistent Activity/participants/student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_remove_participant_not_found(self, client):
        """Test removal of participant who is not registered"""
        response = client.delete(
            "/activities/Soccer Team/participants/notregistered@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Participant not found in this activity"
    
    def test_remove_participant_with_special_characters(self, client):
        """Test removal with email containing special characters"""
        # First add a participant with special characters
        client.post("/activities/Soccer Team/signup?email=special.user%2Btest@mergington.edu")
        
        # Then remove them
        response = client.delete(
            "/activities/Soccer Team/participants/special.user+test@mergington.edu"
        )
        assert response.status_code == 200


class TestRootEndpoint:
    """Test GET / endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestIntegrationScenarios:
    """Test complete user scenarios"""
    
    def test_signup_and_remove_workflow(self, client):
        """Test complete workflow of signing up and removing a participant"""
        email = "workflow@mergington.edu"
        activity = "Swimming Club"
        
        # Get initial participant count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count + 1
        assert email in response.json()[activity]["participants"]
        
        # Remove participant
        remove_response = client.delete(f"/activities/{activity}/participants/{email}")
        assert remove_response.status_code == 200
        
        # Verify removal
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count
        assert email not in response.json()[activity]["participants"]
    
    def test_multiple_signups_different_activities(self, client):
        """Test signing up the same student for multiple activities"""
        email = "multitask@mergington.edu"
        
        # Sign up for multiple activities
        response1 = client.post(f"/activities/Soccer Team/signup?email={email}")
        response2 = client.post(f"/activities/Swimming Club/signup?email={email}")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify participant is in both activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Soccer Team"]["participants"]
        assert email in activities_data["Swimming Club"]["participants"]
