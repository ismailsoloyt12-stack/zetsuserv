#!/usr/bin/env python
"""Test script to verify that new orders start with 0% progress."""

from zetsu import create_app, db
from zetsu.models import Request, OrderProgress
from zetsu.routes_public import create_default_progress_steps

def test_initial_progress():
    """Test that new orders start with 0% progress."""
    app = create_app()
    
    with app.app_context():
        # Create a test request
        test_request = Request(
            client_name="Test User",
            client_email="test@example.com",
            phone="555-1234",
            project_title="Test Project",
            project_type="landing_page",
            pages_required=5,
            budget="$1000-5000",
            details="Test project details",
            status='new'
        )
        
        # Add to database
        db.session.add(test_request)
        db.session.commit()
        
        # Create default progress steps
        create_default_progress_steps(test_request)
        
        # Get progress steps
        progress_steps = test_request.progress_steps.all()
        
        print(f"\n✅ Test Results:")
        print(f"================")
        print(f"Number of steps created: {len(progress_steps)}")
        
        # Check each step
        all_pending = True
        for step in progress_steps:
            print(f"\nStep {step.step_number}: {step.step_name}")
            print(f"  Status: {step.status}")
            print(f"  Progress: {step.progress_percentage}%")
            
            if step.status != 'pending' or step.progress_percentage != 0:
                all_pending = False
                print(f"  ⚠️ WARNING: Step should be pending with 0% progress!")
        
        # Calculate overall progress (same logic as in track_order)
        completed_steps = sum(1 for step in progress_steps if step.status == 'completed')
        in_progress_sum = sum(step.progress_percentage or 0 for step in progress_steps if step.status == 'in_progress')
        
        if len(progress_steps) > 0:
            step_weight = 100.0 / len(progress_steps)
            overall_progress = int((completed_steps * step_weight) + (in_progress_sum * step_weight / 100))
        else:
            overall_progress = 0
        
        print(f"\n📊 Overall Progress Calculation:")
        print(f"  Completed steps: {completed_steps}")
        print(f"  In-progress sum: {in_progress_sum}%")
        print(f"  Overall progress: {overall_progress}%")
        
        # Clean up test data
        for step in progress_steps:
            db.session.delete(step)
        db.session.delete(test_request)
        db.session.commit()
        
        # Final result
        print(f"\n{'='*50}")
        if all_pending and overall_progress == 0:
            print(f"✅ SUCCESS: New orders start with 0% progress!")
        else:
            print(f"❌ FAILURE: Progress is {overall_progress}% instead of 0%")
        print(f"{'='*50}\n")
        
        return overall_progress == 0

if __name__ == "__main__":
    success = test_initial_progress()
    exit(0 if success else 1)