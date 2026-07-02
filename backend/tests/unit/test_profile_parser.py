from app.features.imports.profile_parser import extract_profiles


def test_extract_profiles_finds_repositories_live_links_and_achievements():
    text = """
    GitHub: https://github.com/alex-dev/vision-demo
    LeetCode: https://leetcode.com/u/alex_dev/
    Codeforces: https://codeforces.com/profile/alex.dev
    Kaggle: https://kaggle.com/alexdata
    Scholar: https://scholar.google.com/citations?user=abcDEF12
    Live app: https://vision-demo.vercel.app
    Winner, university AI hackathon 2025.
    Published paper on computer vision systems.
    """

    profiles = extract_profiles(text)

    assert profiles.github_username == "alex-dev"
    assert profiles.github_repositories == ["https://github.com/alex-dev/vision-demo"]
    assert profiles.leetcode_username == "alex_dev"
    assert profiles.codeforces_username == "alex.dev"
    assert profiles.kaggle_username == "alexdata"
    assert profiles.scholar_id == "abcDEF12"
    assert profiles.live_links == ["https://vision-demo.vercel.app"]
    assert len(profiles.achievements) == 2


def test_extract_profiles_skips_non_user_paths():
    text = """
    https://github.com/settings/profile
    https://leetcode.com/problems/two-sum
    https://github.com/octo-org/real-project
    """

    profiles = extract_profiles(text)

    assert profiles.github_username == "octo-org"
    assert profiles.leetcode_username is None
    assert profiles.github_repositories == ["https://github.com/octo-org/real-project"]
