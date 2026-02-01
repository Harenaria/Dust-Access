import dataclasses
import logging
import copy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, TypeVar, Type, get_origin, get_args

logger = logging.getLogger("Serialization")


_MUTABLE_FIELDS_CACHE = {}

def _fast_clone(obj):
    """Deep clones mutable collections and objects with .clone() methods. Optimized for speed."""
    if obj is None:
        return None
    
    obj_type = type(obj)
    
    if obj_type is list:
        # Non-recursive for elements unless they are themselves collections (rare in this state)
        # In this game, lists are mostly Cards or primitives
        return [x.clone() if hasattr(x, 'clone') else x for x in obj]
    if obj_type is dict:
        return {k: (v.clone() if hasattr(v, 'clone') else v) for k, v in obj.items()}
    if obj_type is set:
        return obj.copy()
    
    # Check for cloneable objects
    if hasattr(obj, 'clone'):
        return obj.clone()
        
    return obj

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

    def clone(self):
        """
        High-performance generic clone.
        Uses shallow copy + targeted deep copy of mutable fields only.
        """
        new_obj = copy.copy(self)
        
        cls = self.__class__
        # Caching field names that need deep-cloning for this class
        if cls not in _MUTABLE_FIELDS_CACHE:
            mutable = []
            # We use dataclasses.fields to be strict about what is state
            for f in dataclasses.fields(cls):
                val = getattr(self, f.name)
                # If the field is a collection or has a clone method, it's mutable/deep-copyable
                if isinstance(val, (list, dict, set)) or (val is not None and hasattr(val, 'clone')):
                    mutable.append(f.name)
            _MUTABLE_FIELDS_CACHE[cls] = mutable
            
        # Perform targeted deep copies
        for attr in _MUTABLE_FIELDS_CACHE[cls]:
            val = getattr(self, attr)
            if val is not None:
                setattr(new_obj, attr, _fast_clone(val))
        
        return new_obj

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
        for key, target_type in field_types.items():
            value = data.get(key)
            
            if value is None:
                # Handle missing field: try to find a default
                for f in dataclasses.fields(cls):
                    if f.name == key:
                        if f.default is not dataclasses.MISSING:
                            init_args[key] = f.default
                        elif f.default_factory is not dataclasses.MISSING:
                            init_args[key] = f.default_factory()
                        else:
                            # Mandatory field is missing. Fallback for collections to avoid crash
                            origin = get_origin(target_type)
                            if origin is list: init_args[key] = []
                            elif origin is set: init_args[key] = set()
                            elif origin is dict: init_args[key] = {}
                        break
                if key in init_args: continue
                if value is None: continue # Skip if still None and not a collection

            # 1. Handle Enums
            if isinstance(target_type, type) and issubclass(target_type, Enum):
                try:
                    init_args[key] = target_type(value)
                except (ValueError, TypeError):
                    init_args[key] = value

            # 2. Handle Lists and Sets
            elif get_origin(target_type) in [list, set]:
                inner_args = get_args(target_type)
                inner_type = inner_args[0] if inner_args else Any

                processed_items = []
                # Ensure value is iterable
                items_to_process = value if isinstance(value, (list, set, tuple)) else []
                for item in items_to_process:
                    if dataclasses.is_dataclass(inner_type) and hasattr(inner_type, 'dict_deserializer'):
                        processed_items.append(inner_type.dict_deserializer(item))
                    elif isinstance(inner_type, type) and issubclass(inner_type, Enum):
                        processed_items.append(inner_type(item))
                    else:
                        processed_items.append(item)
                
                init_args[key] = set(processed_items) if get_origin(target_type) is set else processed_items

            # 3. Handle Nested Dataclasses
            elif dataclasses.is_dataclass(target_type) and hasattr(target_type, 'dict_deserializer'):
                init_args[key] = target_type.dict_deserializer(value)

            # 4. Basic Types
            else:
                init_args[key] = value

        return cls(**init_args)