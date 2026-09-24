import pytest

from cfregions_gui import cli


def test_cli_forwards_dataset_options(monkeypatch: pytest.MonkeyPatch) -> None:
    received: dict[str, object] = {}

    def fake_run_gui(**kwargs: object) -> int:
        received.update(kwargs)
        return 7

    monkeypatch.setattr(cli, "run_gui", fake_run_gui)

    result = cli.main(
        [
            "--cf-version",
            "3",
            "--profile",
            "test-profile",
            "--profile-version",
            "2",
            "--data-directory",
            "example-data",
            "--profile-directory",
            "profiles-a",
            "--profile-directory",
            "profiles-b",
        ]
    )

    assert result == 7
    assert received["cf_version"] == "3"
    assert received["profile"] == "test-profile"
    assert received["profile_version"] == "2"
    assert str(received["data_directory"]) == "example-data"
    assert [str(path) for path in received["profile_directories"]] == [
        "profiles-a",
        "profiles-b",
    ]
    assert received["argv"] == ["cfregions-gui"]


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        cli.main(["--version"])

    assert raised.value.code == 0
    assert capsys.readouterr().out.startswith("cfregions-gui ")
