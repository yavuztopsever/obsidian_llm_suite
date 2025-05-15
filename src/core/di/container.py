from typing import Dict, Any, Optional, Type

class ServiceContainer:
    """Simple service locator for dependency management."""
    
    _instances = {}
    
    @classmethod
    def register(cls, service_name: str, instance: Any) -> None:
        """Register a service instance.
        
        Args:
            service_name: The name of the service.
            instance: The service instance.
        """
        cls._instances[service_name] = instance
        
    @classmethod
    def get(cls, service_name: str) -> Any:
        """Get a service instance.
        
        Args:
            service_name: The name of the service.
            
        Returns:
            The service instance.
            
        Raises:
            ValueError: If the service is not registered.
        """
        if service_name not in cls._instances:
            raise ValueError(f"Service {service_name} not registered")
        return cls._instances[service_name]
        
    @classmethod
    def has(cls, service_name: str) -> bool:
        """Check if a service is registered.
        
        Args:
            service_name: The name of the service.
            
        Returns:
            True if the service is registered, False otherwise.
        """
        return service_name in cls._instances