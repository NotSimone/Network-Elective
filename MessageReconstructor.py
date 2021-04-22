from typing import List, Set

from Server import Server, SnoopedPacket


class MessageReconstructor:
    all_packets: List[SnoopedPacket] = []           # All packets we capture
    invalid_message_length: List[int] = list()      # Message lengths confirmed bad
    start_ident: int                                # Identifier for a starting message
    confirmed_message_length: int = -1
    eof: List[int]

    def __init__(self) -> None:
        self.all_packets = list()
        self.invalid_message_length = list()
        self.start_ident = -1
        self.confirmed_message_length = -1

    # Attempt to reconstruct the whole message
    # Returns the message if it can reconstruct it or else return an empty string
    def reconstruct_message(self) -> str:
        if self.confirmed_message_length == -1:
            # Get list of packet ident where the message had an EOF
            self.eof: List[int] = [x.packet_ident for x in self.all_packets if x.message[-1] == "\x04"]

            if len(self.eof) < 3:
                return ""

            # Get list of differences in length and determine possible message lengths
            eof_distance = [self.eof[x+1] - self.eof[x] for x in range(len(self.eof) - 1)]
            # Get the factors for each eof distance
            eof_distance_factors = list(map(lambda x: factors(abs(x)), eof_distance))
            # Get the common factors for the eof distances
            common_eof_distance_factors = list(set.intersection(*eof_distance_factors))
            # Rule out the known bad lengths and we should be left with possible message lengths
            possible_message_len = [x for x in common_eof_distance_factors if x not in self.invalid_message_length]

            print(f"Possible message len: {possible_message_len}")

            # Check if we have only a single message length left
            if len(possible_message_len) == 1:
                self.confirmed_message_length = possible_message_len[0]
            elif len(possible_message_len) == 0:
                print(f"Error: 0 length message len - resetting")
                self = MessageReconstructor()
        else:
            possible_message_len = [self.confirmed_message_length]

        # Check each possible message length
        for message_len in possible_message_len:
            message = self._validate_message_len(message_len)
            if (message):
                # Only return messages we confirm are good
                return message
        return ""


    # Attempt to construct a message with length
    # Returns empty string on fail
    def _validate_message_len(self, length: int) -> str:
        messages: List[str] = [""] * length
        # Check validity using all the packets we found so far
        for x in self.all_packets:
            index = (x.packet_ident - self.eof[0] - 1) % length
            if messages[index] == "":
                messages[index] = x.message
            else:
                # On mismatch, mark length as invalid and return
                if messages[index] != x.message:
                    self.invalid_message_length.append(length)
                    return ""

        # Check if we found a whole message
        missing_messages = [x for x in messages if x == ""]
        if len(missing_messages) == 0:
            complete_message = "".join(messages)
            print(f"Complete message: {complete_message}")
            return complete_message

        if self.confirmed_message_length != -1:
            print(f"{len(missing_messages)} missing messages")

        return ""

# Get factors of a number
# https://stackoverflow.com/questions/6800193/what-is-the-most-efficient-way-of-finding-all-the-factors-of-a-number-in-python
def factors(n) -> Set[int]:
    return set(x for tup in ([i, n//i] 
                for i in range(1, int(n**0.5)+1) if n % i == 0) for x in tup)
