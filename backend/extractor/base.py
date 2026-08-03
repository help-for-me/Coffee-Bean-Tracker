from abc import ABC, abstractmethod


class BeanExtractor(ABC):
    @abstractmethod
    def extract(self, image_bytes_list: list[bytes]) -> dict:
        """Takes 1+ images, returns a dict matching the extraction schema, None for anything not visible."""
        ...
