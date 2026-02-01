"""
Pytest configuration and fixtures.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def sample_python_code():
    """Sample Python code for parser tests."""
    return '''
import os
from typing import List

class Calculator:
    """A simple calculator class."""
    
    def __init__(self):
        self.result = 0
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
    
    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b


def fibonacci(n: int) -> List[int]:
    """Generate fibonacci sequence."""
    if n <= 0:
        return []
    if n == 1:
        return [0]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib
'''


@pytest.fixture
def sample_javascript_code():
    """Sample JavaScript code for parser tests."""
    return '''
import { useState } from 'react';

class UserService {
    constructor(apiEndpoint) {
        this.apiEndpoint = apiEndpoint;
    }
    
    async getUser(id) {
        const response = await fetch(`${this.apiEndpoint}/users/${id}`);
        return response.json();
    }
}

function formatName(firstName, lastName) {
    return `${firstName} ${lastName}`;
}

const greet = (name) => {
    return `Hello, ${name}!`;
};

export { UserService, formatName, greet };
'''
