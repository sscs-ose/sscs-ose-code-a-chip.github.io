class RegisterFile:
    """
    Simplified RISC-V integer register file.

    Contains 32 integer registers:
        x0 - x31

    x0 is permanently hardwired to zero.
    """

    NUM_REGISTERS = 32

    def __init__(self) -> None:
        self._registers = [0] * self.NUM_REGISTERS

    def read(self, register_number: int) -> int:
        """
        Read the value of a register.
        """

        self._validate_register(register_number)

        return self._registers[register_number]

    def write(self, register_number: int, value: int) -> None:
        """
        Write a value to a register.

        x0 cannot be modified.
        """

        self._validate_register(register_number)

        if register_number == 0:
            return

        self._registers[register_number] = value

    def reset(self) -> None:
        """
        Reset all registers to zero.
        """

        self._registers = [0] * self.NUM_REGISTERS

    def get_all(self) -> list[int]:
        """
        Return a copy of all register values.
        """

        return self._registers.copy()

    def _validate_register(self, register_number: int) -> None:
        """
        Ensure register number is between x0 and x31.
        """

        if type(register_number) is not int or not 0 <= register_number < self.NUM_REGISTERS:
            raise ValueError(
                f"Invalid RISC-V register x{register_number}. "
                "Register number must be an integer between 0 and 31."
            )
