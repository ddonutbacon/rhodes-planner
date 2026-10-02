from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "main.py").read_text(encoding="utf-8")


def test_account_resources_are_not_committed_on_render():
    # Regression for v1.4.0: keyed number_input widgets used to overwrite the
    # imported Inventory object on every Streamlit rerun.
    assert 'inv.lmd = c1.number_input(' not in APP
    assert 'inv.exp_cards[iid] = col.number_input(' not in APP
    assert 'account_resources_form_' in APP


def test_no_global_end_of_run_profile_commit():
    # Profile commits should happen at explicit mutation points, not blindly at
    # the end of every rerun where transient widget state can clobber account data.
    assert '# Persist normalized state at the end of every successful run.' not in APP


def test_credits_are_first_navigation_page():
    marker = '["Credits & Sources", "Dashboard", "Account", "Planner", "Farming", "About"]'
    assert marker in APP


def test_saved_plan_has_edit_and_remove_actions():
    assert '"✏️ Edit"' in APP
    assert '"🗑 Remove"' in APP
    assert 'editing_goal_id' in APP


def test_penguin_export_is_copy_first_not_download_first():
    assert 'clipboard_button(' in APP
    assert 'Copy Penguin Statistics config' in APP
    assert 'Download Penguin Statistics Planner config' not in APP
