<!--
  Licensed to the Apache Software Foundation (ASF) under one or more
  contributor license agreements.  See the NOTICE file distributed with
  this work for additional information regarding copyright ownership.
  The ASF licenses this file to You under the Apache License, Version 2.0
  (the "License"); you may not use this file except in compliance with
  the License.  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.

  Copyright (c) 2026 HePin
-->

# PI for Qoder

Qoder is a coding agent platform. To enable PI monitoring and visualization in Qoder, you can use the generic PI hooks and (optionally) the Qoder adapter in this directory.

## Integration

If Qoder supports shell hooks or post-command execution:

1. **Capture (generic) events**: pipe JSON (or any text) into the generic capture hook. The hook writes privacy-sanitized nodes into `~/.pi/decisions/YYYY-MM-DD/session-*.nodes.jsonl`.
   
   ```bash
   qoder ... | ../hooks/capture-generic.sh
   ```

   If you can also populate `PI_SESSION_ID`, you can keep a stable session identity across multiple commands.

2. **Visualize**: use the standard PI visualizer.

   Offline HTML:
   ```bash
   cd /path/to/pi/visualize && mill frontend.standaloneHtml && mill cli.run
   ```

   Live local preview (loopback server + polling):
   ```bash
   cd /path/to/pi/visualize && mill cli.run --live
   ```

## Generic Adapter

We provide a generic adapter script `pi-qoder-adapter.sh` in this directory. You can wrap your Qoder commands with it.

```bash
./pi-qoder-adapter.sh qoder do-something
```
