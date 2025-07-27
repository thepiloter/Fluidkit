# Type System & FluidTypes

FluidKit's intelligent type conversion from Python to TypeScript with clean handling of external types.

## Type Boundaries

FluidKit categorizes types based on project boundaries:

### **Project Types** → Full TypeScript Interfaces
Types defined within your project get complete introspection and generate proper TypeScript interfaces.

```python
# Your project code
class User(BaseModel):
    name: str
    email: str
```

```typescript
// Generated TypeScript
export interface User {
  name: string;
  email: string;
}
```

### **External Types** → FluidTypes Namespace or `any`
Types from outside your project are handled differently:

- **Common external types** → Clean `FluidTypes` namespace
- **Uncommon external types** → TypeScript `any` type

## FluidTypes Namespace

Common external types get mapped to the `FluidTypes` namespace for clean, conflict-free usage:

```python
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pathlib import Path

class Order(BaseModel):
    id: UUID
    total: Decimal
    created_at: datetime
    file_path: Path
```

```typescript
import type { FluidTypes } from './.fluidkit/runtime';

export interface Order {
  id: FluidTypes.UUID;
  total: FluidTypes.Decimal;
  created_at: FluidTypes.DateTime;
  file_path: FluidTypes.Path;
}
```

## JSDoc Documentation

FluidKit automatically generates helpful JSDoc comments for external types:

```typescript
export interface Order {
  /** @external Python uuid.UUID -> string */
  id: FluidTypes.UUID;
  
  /** @external Python decimal.Decimal -> number */
  total: FluidTypes.Decimal;
  
  /** @external Python datetime.datetime -> string */
  created_at: FluidTypes.DateTime;
}
```

IDE tooltips show the original Python type and conversion, making it clear where external types come from and how they're serialized.

## Type Mapping Reference

| Python Type | TypeScript Output | Notes |
|-------------|------------------|-------|
| `str` | `string` | Basic primitive |
| `int`, `float` | `number` | Basic primitive |
| `bool` | `boolean` | Basic primitive |
| `list[T]` | `T[]` | Array conversion |
| `dict[str, T]` | `Record<string, T>` | Object mapping |
| `Optional[T]` | `T \| null` | Union with null |
| `Union[A, B]` | `A \| B` | TypeScript union |
| **Project Models** | **Full Interface** | **Complete introspection** |
| `UUID` | `FluidTypes.UUID` | → `string` |
| `Decimal` | `FluidTypes.Decimal` | → `number` |
| `datetime` | `FluidTypes.DateTime` | → `string` (ISO) |
| `date` | `FluidTypes.Date` | → `string` (ISO) |
| `Path` | `FluidTypes.Path` | → `string` |
| `EmailStr` | `FluidTypes.EmailStr` | → `string` |
| `HttpUrl` | `FluidTypes.HttpUrl` | → `string` |
| `PaymentCardNumber` | `FluidTypes.PaymentCardNumber` | → `string` |
| **Other External** | **`any`** | **Future improvement** |

## Usage Examples

### Complex Types with FluidTypes

```python
from typing import Optional
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, EmailStr

class UserProfile(BaseModel):
    user_id: UUID
    email: EmailStr
    balance: Optional[Decimal]
    preferences: dict[str, str]
```

```typescript
import type { FluidTypes } from './.fluidkit/runtime';

export interface UserProfile {
  user_id: FluidTypes.UUID;
  email: FluidTypes.EmailStr;
  balance?: FluidTypes.Decimal | null;
  preferences: Record<string, string>;
}
```

### Importing FluidTypes

```typescript
// Only imports the namespace when needed
import type { FluidTypes } from './.fluidkit/runtime';
import type { User } from './models';

// Clean usage without conflicts
const userId: FluidTypes.UUID = "123e4567-e89b-12d3-a456-426614174000";
const user: User = await getUser(userId);
```

## Benefits

- **Zero Conflicts**: `FluidTypes.UUID` vs custom `UUID` interface never conflict
- **Type Safety**: External types maintain proper TypeScript typing
- **Clean Imports**: Only import the namespace when external types are used
- **IDE Support**: JSDoc annotations explain type origins and conversions
- **Future-Proof**: New external types can be added to namespace easily

The type system ensures your FastAPI models translate perfectly to TypeScript while handling external dependencies cleanly.
