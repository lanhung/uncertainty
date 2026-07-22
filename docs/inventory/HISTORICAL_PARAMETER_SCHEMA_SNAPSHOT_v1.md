# Historical standard-BBN parameter-schema snapshot v1

Status: immutable compatibility snapshot

The registered W0–W3 runtime and numerical artifacts were executed against
`configs/physics/parameter_schema.yaml` before the manuscript-first pivot in
ADR-0005. That exact byte sequence is retained as
`configs/physics/parameter_schema_standard_bbn_v1.yaml`, with SHA256
`61dc9c3ec1fdc9eb455f9ed64ad604a49d801e2b7de361db8db74a883b8c3c9e`.

The canonical `parameter_schema.yaml` now contains the manuscript stiff-model
semantics and has a different hash. Historical artifact validators therefore
bind to the immutable snapshot; they do not reinterpret an old run using the
new schema. New manuscript/UQ runs must bind the current canonical schema or a
new explicitly versioned successor.
