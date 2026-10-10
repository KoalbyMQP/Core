import time

from Crab import Crab, TicketType
from HerkuleX import HerkuleX, JogLedColor


def main():
    bridge_file = "bridge.toml"
    crab = Crab(bridge_file, True)

    while True:
        print("Health check #1")
        crab.GetHealth("AckCheck")

        print("Waiting for 3 seconds ...")
        time.sleep(3)

        print("Moving shoulder")
        command = HerkuleX.MoveOne("Test", float(-23), 40, JogLedColor.LED_BLUE)
        ticket = crab.send(TicketType.Interrupt, [command], None, False)
        print("Ticket created. Here it is:")
        print(f"{ticket}")

        time.sleep(1)
        print("\n\n\n\n\n\n")
        command = HerkuleX.MoveOne("Test", float(23), 40, JogLedColor.LED_RED)
        ticket = crab.send(TicketType.Asynchronous, [command], None, False)
        print("Main:ticket" + str(ticket))

        print("Health check #2")
        crab.GetHealth("AckCheck")

        print("Waiting for 3 seconds ...")
        time.sleep(3)


if __name__ == "__main__":
    main()
