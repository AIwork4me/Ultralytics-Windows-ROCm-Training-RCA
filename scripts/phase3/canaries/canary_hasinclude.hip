// G57-2: __has_include(<type_traits>) semantics inside a wheel hiprtc
// compile. Writes 1 when the probe resolves a real header, 0 when not.
// Run twice: default env (expect 1: MSVC auto-discovery) and -nostdinc
// (expect 0). This validates the Design-D discriminator end to end.
extern "C" __global__ void canary_hasinclude(int* out)
{
#if __has_include(<type_traits>)
    *out = 1;
#else
    *out = 0;
#endif
}
