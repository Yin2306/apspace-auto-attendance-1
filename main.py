import re
from sys import argv

import requests
from yaml import safe_load


class Account:
    # Ticket granting ticket (TGT)
    TGT_URL = "https://cas.apiit.edu.my/cas/v1/tickets"
    TGT_PATTERN = r'TGT-[^"]*'

    # Service ticket (ST)
    ATTENDIX_SERVICE_URL = "https://api.apiit.edu.my/attendix"

    # Attendance
    ATTENDIX_URL = "https://attendix.apu.edu.my/graphql"

    def __init__(self, username: str, password: str, api_key: str) -> None:
        """Initialize an Account object.

        Parameters
        ----------
        username : str
            APSpace username.
        password : str
            APSpace password.
        api_key : str
            API key for APSpace.
        """

        self.username = username
        self.password = password
        self.api_key = api_key
        self.tgt = None
        self.service_ticket = None

    def login(self) -> None:
        """Log in to APSpace and get ticket granting ticket (TGT).

        Raises
        ------
        ValueError
            If failed to get TGT.
        """
        data = {"username": self.username, "password": self.password}
        response = requests.post(self.TGT_URL, data)

        match = re.search(self.TGT_PATTERN, response.text)
        if not match:
            raise ValueError(f"Failed to get TGT for {self.username}")

        self.tgt = match.group()

    def get_service_ticket(self, service: str) -> None:
        """
        Obtain a service ticket for a specified service using the stored TGT.

        Parameters
        ----------
        service : str
            The service URL for which to obtain a ticket.

        Raises
        ------
        ValueError
            If the TGT is not found or if the request to obtain a service ticket fails.
        """

        if not self.tgt:
            raise ValueError("TGT not found")

        url = f"{self.TGT_URL}/{self.tgt}?service={service}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(url, headers=headers)

        if not response.text:
            raise ValueError(
                f"Failed to get service ticket for {self.username} and service {service}"
            )

        self.service_ticket = response.text

    def take_attendance(self, otp: str) -> None:
        """
        Take attendance for the user using the given OTP.

        Parameters
        ----------
        otp : str
            The one-time password to take attendance.

        Raises
        ------
        ValueError
            If the service ticket is not found or if there are errors in the response.
        """

        if not self.service_ticket:
            raise ValueError("Service ticket not found")

        json = {
            "operationName": "updateAttendance",
            "query": "mutation updateAttendance($otp: String!) {\n  updateAttendance(otp: $otp) {\n    id\n    attendance\n    classcode\n    date\n    startTime\n    endTime\n    classType\n    __typename\n  }\n}\n",
            "variables": {"otp": otp},
        }
        headers = {"Ticket": self.service_ticket, "x-api-key": self.api_key}
        response = requests.post(self.ATTENDIX_URL, json=json, headers=headers)
        response_dict = response.json()

        if "errors" in response_dict:
            messages = (error["message"] for error in response_dict["errors"])
            raise ValueError(
                f"Failed to take attendance for {self.username}: {'; '.join(messages)}"
            )

        print("attendance:")
        print(response_dict)

    def __str__(self) -> str:
        return f"Account(username={self.username})"


def bulk_login_and_take_attendance(account_file_path: str, otp: str) -> None:
    """
    Log in to APSpace and take attendance for multiple accounts using the given OTP.

    Parameters
    ----------
    account_file_path : str
        Path to the YAML file containing the account information.
    otp : str
        The one-time password to take attendance.

    Raises
    ------
    ValueError
        If the OTP is invalid, or if there are errors during the login and attendance taking process.
    """

    with open(account_file_path) as file:
        accounts = safe_load(file)
    count = len(accounts)

    if not otp.isdigit() or len(otp) != 3:
        raise ValueError(f"Invalid OTP '{otp}'")

    for index, account_dict in enumerate(accounts, start=1):
        print(f"{index}/{count}")
        try:
            account = Account(**account_dict)
            print(account)
            account.login()
            account.get_service_ticket(Account.ATTENDIX_SERVICE_URL)
            account.take_attendance(otp)
            print("Attendance taken")
        except Exception as e:
            print(f"ERROR: {e}")
        print()
    print("Done")


def main() -> None:
    account_file_path = "accounts.yaml"

    if len(argv) < 2:
        raise ValueError("Usage: python main.py <otp>")
    otp = argv[1]

    bulk_login_and_take_attendance(account_file_path, otp)


if __name__ == "__main__":
    main()
