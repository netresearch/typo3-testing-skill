# Event Dispatch Testing Patterns

## Testing Try/Catch Guarded Event Dispatch

When event dispatch is wrapped in try/catch for robustness, both the success and exception paths need testing.

### Pattern: Guarded Dispatch

```php
// Production code
try {
    $event = $this->eventDispatcher->dispatch(
        new ImageProcessedEvent($filePath, $result)
    );
} catch (\Throwable $e) {
    $this->logger->error('Event listener failed', ['exception' => $e]);
}
```

### Test: Success Path

```php
public function testEventIsDispatched(): void
{
    $eventDispatcher = $this->createMock(EventDispatcherInterface::class);
    $eventDispatcher->expects(self::once())
        ->method('dispatch')
        ->with(self::isInstanceOf(ImageProcessedEvent::class))
        ->willReturnArgument(0);

    // ... invoke production code ...
}
```

### Test: Exception Path (Catch Block)

```php
public function testEventDispatchFailureIsLogged(): void
{
    $eventDispatcher = $this->createMock(EventDispatcherInterface::class);
    $eventDispatcher->method('dispatch')
        ->willThrowException(new \RuntimeException('Listener failed'));

    $logger = $this->createMock(LoggerInterface::class);
    $logger->expects(self::once())
        ->method('error')
        ->with(
            self::stringContains('Event listener failed'),
            self::arrayHasKey('exception')
        );

    // ... invoke production code, verify it doesn't throw ...
}
```

## Testing PHP Warning/Error Functions

Functions like `getimagesize()`, `file_get_contents()` with invalid input trigger PHP warnings.

### Pattern: Suppressed Warning with Return Check

```php
// Production code
$size = @getimagesize($filePath);
if ($size === false) {
    throw new InvalidImageException('Cannot read image dimensions');
}
```

### Test: Warning Trigger Path

```php
public function testInvalidImageThrowsException(): void
{
    $this->expectException(InvalidImageException::class);
    // Pass a non-image file to trigger the getimagesize failure
    $processor->getImageDimensions('/path/to/not-an-image.txt');
}
```

### When to Use @ Suppression

| Context | @ OK? | Reason |
|---------|-------|--------|
| `@mkdir($dir, 0775, true)` | Yes | TOCTOU race condition — dir may be created between check and create |
| `@file_get_contents($path)` | Yes | If return value is checked (`=== false`) |
| `@getimagesize($path)` | Yes | If return value is checked (`=== false`) |
| `@unlink($path)` | Depends | OK in cleanup, not OK if deletion is critical |
