from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.main import app


@pytest.fixture
def client() -> TestClient:
    """Synchronous test client."""
    return TestClient(app)

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous test client for testing async endpoints."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def mock_repo_data():
    """Sample repository data for testing."""
    return {
        "url": "https://github.com/fastapi/fastapi",
        "owner": "fastapi",
        "name": "fastapi",
        "id": "test-repo-id"
    }

@pytest.fixture
def sample_python_code():
    return """
import os
import sys

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class Calculator:
    def add(self, a, b):
        return a + b
"""

@pytest.fixture
def sample_javascript_code():
    return """
function formatName(firstName, lastName) {
    return firstName + " " + lastName;
}

class User {
    constructor(name) {
        this.name = name;
    }
}
"""


@pytest.fixture
def sample_go_code():
    return """
package main

import "fmt"

type Greeter struct {}

func (g Greeter) Greet(name string) string {
    return fmt.Sprintf("Hello %s", name)
}

func add(a int, b int) int {
    return a + b
}
"""


@pytest.fixture
def sample_rust_code():
    return """
use std::fmt;

struct Counter {
    value: i32,
}

impl Counter {
    fn increment(&mut self) {
        self.value += 1;
    }
}

fn sum(a: i32, b: i32) -> i32 {
    a + b
}
"""


@pytest.fixture
def sample_csharp_code():
    return """
using System;

public class Calculator
{
    public int Add(int a, int b)
    {
        return a + b;
    }
}
"""


@pytest.fixture
def sample_cpp_code():
    return """
#include <string>

class Greeter {
public:
    std::string greet(const std::string& name) { return "Hello " + name; }
};

int add(int a, int b) {
    return a + b;
}
"""


@pytest.fixture
def sample_ruby_code():
    return """
require "json"

module Billing
  class Invoice
    def total(a, b)
      a + b
    end
  end
end

def helper(name)
  "Hello #{name}"
end
"""
