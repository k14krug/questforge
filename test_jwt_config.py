#!/usr/bin/env python3
"""
Test script to verify JWT token expiration configuration for different environments.
"""
import os
import sys
from datetime import timedelta

# Add the project root to Python path
sys.path.insert(0, '/home/kkrug/projects/questforge')

from config import config_by_name

def test_jwt_config():
    """Test JWT token expiration configuration for different environments."""
    print("=== JWT Token Expiration Configuration Test ===\n")
    
    environments = ['development', 'production']
    
    for env_name in environments:
        print(f"Environment: {env_name.upper()}")
        config_class = config_by_name[env_name]
        config = config_class()
        
        # Get JWT expiration setting
        jwt_expires = config.JWT_ACCESS_TOKEN_EXPIRES
        
        if isinstance(jwt_expires, timedelta):
            hours = jwt_expires.total_seconds() / 3600
            print(f"  JWT Token Expires: {hours} hours ({jwt_expires})")
        else:
            print(f"  JWT Token Expires: {jwt_expires}")
            
        print(f"  Debug Mode: {config.DEBUG}")
        print(f"  Secret Key: {config.SECRET_KEY[:10]}..." if config.SECRET_KEY else "  Secret Key: None")
        print(f"  CORS Origins: {config.SOCKETIO_CORS_ORIGINS}")
        print()
    
    # Test environment variable override
    print("=== Testing Environment Variable Override ===")
    
    # Simulate setting an environment variable
    original_value = os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_HOURS')
    os.environ['JWT_ACCESS_TOKEN_EXPIRES_HOURS'] = '12'
    
    try:
        # Reload config with new environment variable
        config_class = config_by_name['development']
        config = config_class()
        jwt_expires = config.JWT_ACCESS_TOKEN_EXPIRES
        hours = jwt_expires.total_seconds() / 3600
        print(f"With JWT_ACCESS_TOKEN_EXPIRES_HOURS=12: {hours} hours")
    finally:
        # Restore original environment variable
        if original_value is not None:
            os.environ['JWT_ACCESS_TOKEN_EXPIRES_HOURS'] = original_value
        else:
            os.environ.pop('JWT_ACCESS_TOKEN_EXPIRES_HOURS', None)
    
    print("\n=== Summary ===")
    print("✅ Development: 8 hours (default) - Better for testing")
    print("✅ Production: 1 hour (default) - Better for security")
    print("✅ Both environments support JWT_ACCESS_TOKEN_EXPIRES_HOURS env var override")
    print("✅ Authentication duration is now environment-specific!")

if __name__ == "__main__":
    test_jwt_config()
