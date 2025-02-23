import re
from typing import Dict, List, Optional

from ner_playground.config import LABEL_MAPPING, TOKENIZER


class Token:
    def __init__(
        self,
        token: str,
        index: int,
        start_index: int,
        end_index: int,
        raw_label: Optional[str] = None,
        bio_label: Optional[str] = None,
    ):
        self.token = token
        self.index = index
        self.start_index = start_index
        self.end_index = end_index
        self.raw_label = raw_label
        self.bio_label = bio_label

    def __repr__(self):
        return (
            f"T: {self.token} / "
            f"I: {self.index} / "
            f"S: {self.start_index} / "
            f"E: {self.end_index} / "
            f"RL: {self.raw_label} / "
            f"CL: {self.clean_label} / "
            f"BIO: {self.bio_label}"
        )

    @property
    def bio_idx(self):
        return LABEL_MAPPING[self.bio_label]

    @property
    def clean_label(self):
        return re.sub(r"\s#\d+$", "", self.raw_label)

    def as_dict(self):
        return {
            "token": self.token,
            "index": self.index,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "raw_label": self.raw_label,
            "bio_label": self.bio_label,
        }

    @classmethod
    def from_dict(cls, as_dict: Dict):
        return cls(**as_dict)


def tokenize(text: str):
    '''
    Tokenize text into tokens with start and end index
    '''
    encoded = TOKENIZER.encode_plus(text, return_offsets_mapping=True)
    ids = encoded["input_ids"]
    offsets = encoded["offset_mapping"]
    tokens = TOKENIZER.convert_ids_to_tokens(ids)

    tokens = [
        Token(token=token, index=index, start_index=offset[0], end_index=offset[1])
        for token, index, offset in zip(tokens, ids, offsets)
    ]

    return tokens


def most_frequent(list_of_labels):
    return max(set(list_of_labels), key=list_of_labels.count)


def generate_labeled_tokens(text: str, labels: List[Dict]):
    tokens = tokenize(text=text)

    char_label = ["O"] * len(text)

    for i, span in enumerate(labels):

        label = span["label"]
        start = span["start"]
        end = span["end"]

        char_label[start:end] = [f"{label} #{i}"] * (end - start)

    for i, token in enumerate(tokens):
        if token.start_index != token.end_index:
            token.raw_label = most_frequent(
                char_label[token.start_index : token.end_index]
            )
        else:
            token.raw_label = "O"

    # BIO labels
    for i, token in enumerate(tokens):
        if token.raw_label != "O":
            if i == 0:
                token.bio_label = "B-" + token.clean_label

            else:
                if tokens[i - 1].raw_label == tokens[i].raw_label:
                    token.bio_label = "I-" + token.clean_label
                else:
                    token.bio_label = "B-" + token.clean_label
        else:
            token.bio_label = token.clean_label

    return tokens


def group_tokens_by_entity(tokens: List[Token]):
    """
    List to List[List[Token]]

    :param tokens:
    :return:
    """
    block_tokens = []
    for i, token in enumerate(tokens):
        if token.bio_label == "O" or token.start_index == token.end_index == 0:
            continue
        elif i == 0:
            block_tokens.append([token])
        elif (
            tokens[i].bio_label.split("-")[0] == "B"
            or tokens[i - 1].bio_label.split("-")[-1]
            != tokens[i].bio_label.split("-")[-1]
        ):
            block_tokens.append([token])
        else:
            block_tokens[-1].append(token)

    return block_tokens


def decode_labeled_tokens(tokens: List[Token]):
    """
    decode labeled tokens into word indexes

    :param tokens:
    :return:
    """
    block_tokens = group_tokens_by_entity(tokens=tokens)

    labels = []
    for block in block_tokens:
        start = min(token.start_index for token in block)
        end = max(token.end_index for token in block)
        label = block[0].bio_label.split("-")[-1]
        labels.append({"label": label, "start": start, "end": end})

    return labels
