"""Concealed local password input for the repository distribution."""

import getpass
import sys
import warnings

import case


def hidden_password():
    case.require(sys.stdin.isatty(), "concealed_input_unavailable")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            return getpass.getpass("Document password (local concealed input): ")
        except (getpass.GetPassWarning, EOFError, KeyboardInterrupt):
            raise case.CaseError("concealed_input_unavailable") from None
