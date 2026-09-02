import Lake
open Lake DSL

package collectiveBound where
  leanOptions := #[⟨`autoImplicit, false⟩]

@[default_target]
lean_lib CrossLayer where
  srcDir := "."
  roots := #[`CrossLayer.General, `CrossLayer.AccumulationWitness]
