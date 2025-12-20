import dataclasses
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, TypeVar, Type, get_origin, get_args

logger = logging.getLogger("Serialization")

@dataclass
class DataclassJSONCapable:
    def dict_serializer(self) -> Dict[str, Any]:
        """
        Serializes the object to a dictionary.
        Uses a custom factory to ensure Enums are converted to their values.
        """
        def dict_factory(data):
            result = {}
            for k, v in data:
                if isinstance(v, Enum):
                    result[k] = v.value
                else:
                    result[k] = v
            return result

        return dataclasses.asdict(self, dict_factory=dict_factory)

    T = TypeVar("T", bound="DataclassJSONCapable")
    @classmethod
    def dict_deserializer(cls: Type[T], data: Dict[str, Any]) -> T | None:
        """
        Deserializes a dictionary into a Dataclass, recursively handling
        Nested Dataclasses, Lists of Dataclasses, and Enums.
        """
        if data is None:
            return None

        # Get the type hints for the class (e.g., name: str, cardType: CardType)
        field_types = {f.name: f.type for f in dataclasses.fields(cls)}
        # Prepare the arguments to reconstruct the class
        init_args = {}
        for key, value in data.items():
            # If the JSON key isn't in our class fields, ignore it (or log warning)
            if key not in field_types:
                logger.warning(f"Key {key} not found in {cls.__name__}")
                continue

            target_type = field_types[key]

            # 1. Handle Enums (e.g., target_type is CardType, value is "Weapon")
            if isinstance(target_type, type) and issubclass(target_type, Enum):
                try:
                    init_args[key] = target_type(value)
                except ValueError:
                    # Fallback for robustness
                    init_args[key] = value

            # 2. Handle Lists (e.g., target_type is List[Card])
            elif get_origin(target_type) is list:
                # Extract the inner type (Card) from List[Card]
                inner_type = get_args(target_type)[0]

                # If the inner type is a dataclass, recurse
                if dataclasses.is_dataclass(inner_type) and hasattr(inner_type, 'from_dict'):
                    init_args[key] = [inner_type.from_dict(item) for item in value]
                elif issubclass(inner_type, Enum):
                    init_args[key] = [inner_type(item) for item in value]
                else:
                    init_args[key] = value

            # 3. Handle Nested Dataclasses (e.g., target_type is Deck)
            elif dataclasses.is_dataclass(target_type) and hasattr(target_type, 'from_dict'):
                init_args[key] = target_type.from_dict(value)

            # 4. Basic Types (str, int, bool)
            else:
                init_args[key] = value

        return cls(**init_args)