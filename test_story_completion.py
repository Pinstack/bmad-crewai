#!/usr/bin/env python3
"""Test script to validate story 1.0 completion."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pytest

from bmad_crewai import BmadCrewAI


@pytest.mark.asyncio
async def test_story_completion():
    """Test all story 1.0 functionality."""
    print("🔍 Testing Story 1.0 Completion")
    print("=" * 50)

    bmad = BmadCrewAI()

    async with bmad.session():
        results = {}

        # Test 1: CrewAI Agent Integration (Task 4)
        print("\n📋 Task 4: CrewAI Agent Integration")
        try:
            agent_registration = bmad.register_bmad_agents()
            if agent_registration:
                print("✅ BMAD agents registered successfully")

                agents = bmad.list_bmad_agents()
                print(f"✅ {len(agents)} agents available: {list(agents.keys())}")

                coordination_test = bmad.test_agent_coordination()
                if coordination_test.get("coordination_test"):
                    print("✅ Agent coordination test passed")
                    results["task4"] = True
                else:
                    print("❌ Agent coordination test failed")
                    results["task4"] = False
            else:
                print("❌ Agent registration failed")
                results["task4"] = False

        except Exception as e:
            print(f"❌ Task 4 failed: {e}")
            results["task4"] = False

        # Test 2: Artefact Generation (Task 5)
        print("\n📄 Task 5: Artefact Generation")
        try:
            artefact_test = bmad.test_artefact_generation()
            if all(artefact_test.values()):
                print("✅ All artefact generation tests passed")
                results["task5"] = True
            else:
                failed = [k for k, v in artefact_test.items() if not v]
                print(f"❌ Artefact generation failed: {failed}")
                results["task5"] = False

        except Exception as e:
            print(f"❌ Task 5 failed: {e}")
            results["task5"] = False

        # Test 3: Development Environment (Task 6)
        print("\n🛠️  Task 6: Development Environment")
        try:
            env_test = bmad.test_development_environment()
            if all(env_test.values()):
                print("✅ All development environment tests passed")
                results["task6"] = True
            else:
                failed = [k for k, v in env_test.items() if not v]
                print(f"❌ Development environment tests failed: {failed}")
                results["task6"] = False

        except Exception as e:
            print(f"❌ Task 6 failed: {e}")
            results["task6"] = False

        # Test 4: Quality Gates & Checklists (Task 7)
        print("\n🔒 Task 7: Quality Gates & Checklists")
        try:
            checklists = bmad.list_available_checklists()
            if checklists:
                print(f"✅ {len(checklists)} checklists available")

                # Test checklist execution
                gate_test = bmad.test_quality_gates()
                if all(gate_test.values()):
                    print("✅ All quality gate tests passed")
                    results["task7"] = True
                else:
                    failed = [k for k, v in gate_test.items() if not v]
                    print(f"❌ Quality gate tests failed: {failed}")
                    results["task7"] = False
            else:
                print("❌ No checklists available")
                results["task7"] = False

        except Exception as e:
            print(f"❌ Task 7 failed: {e}")
            results["task7"] = False

        # Summary
        print("\n" + "=" * 50)
        print("📊 STORY COMPLETION SUMMARY")
        print("=" * 50)

        completed_tasks = sum(1 for v in results.values() if v)
        total_tasks = len(results)

        for task, status in results.items():
            status_icon = "✅" if status else "❌"
            print(f"{status_icon} {task.upper()}: {'PASSED' if status else 'FAILED'}")

        print(f"\n🎯 Overall: {completed_tasks}/{total_tasks} tasks completed")

        if completed_tasks == total_tasks:
            print("🎉 STORY 1.0 IS COMPLETE!")
            return True
        else:
            print("⚠️  STORY 1.0 IS INCOMPLETE - Remaining tasks need attention")
            return False


if __name__ == "__main__":
    success = asyncio.run(test_story_completion())
    sys.exit(0 if success else 1)
