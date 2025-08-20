# Claude Development Guidelines

## Code Changes
- Maximum 50 lines per change for easy review
- Each change should be atomic and focused on a single concern
- Break large features into smaller, reviewable chunks

## Testing Requirements
- Every new feature must include unit tests
- Maintain or improve existing test coverage
- Tests should be clear, focused, and independent
- Use descriptive test names that explain the behavior being tested

## Code Quality Standards

### Type Safety
- Use type hints everywhere in Python code
- Define clear interfaces and data models
- Use TypedDict, dataclasses, or Pydantic models for complex data structures
- Avoid using `Any` type unless absolutely necessary

### Code Style
- No emojis or icons in code comments or strings
- Clean, descriptive variable and function names
- Functions should do one thing and do it well
- Keep functions under 20 lines when possible

### Comments and Documentation
- Comment only complex logic that isn't clear from the code itself
- Prefer self-documenting code through clear naming
- Avoid obvious comments that repeat what the code does
- Use docstrings for public APIs and complex functions

### Error Handling
- Use specific exception types
- Handle errors at the appropriate level
- Provide meaningful error messages
- Log errors with sufficient context for debugging

## Project Structure
- Follow existing clean architecture patterns
- Keep domain logic separate from infrastructure concerns
- Use dependency injection for testability
- Maintain consistent folder structure across services

## Change Documentation
- Update the CHANGELOG.md file in each service directory when implementing features
- Document breaking changes, new features, and bug fixes
- Use semantic versioning principles
- Include migration notes when necessary

## Git Workflow
- Make atomic commits with clear, descriptive messages
- Include the affected service in commit messages (e.g. "api-service: add user validation")
- Reference issue numbers when applicable
- Keep commit history clean and readable

## Performance Considerations
- Consider memory and CPU impact of changes
- Use appropriate data structures for the use case
- Implement pagination for large data sets
- Add performance tests for critical paths

## Security Guidelines
- Validate all inputs at service boundaries
- Use parameterized queries for database operations
- Follow principle of least privilege
- Never log sensitive information
- Use secure defaults for configurations