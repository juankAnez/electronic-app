"""
ElectroSmart Platform — Motor de Cálculo Eléctrico
=================================================
Módulo: pipeline.py
Descripción: Orquestador central del motor que secuencia las etapas
             para entregar un objeto de resultado inmutable CircuitResult.
"""

from core.engine.domain import CircuitInput, CircuitResult
from core.engine.stages import (
    CalculationContext,
    NormalizationStage,
    CurrentCalculationStage,
    CorrectionFactorsStage,
    ConductorSelectionStage,
    VoltageDropStage,
    IterativeResizeStage,
    BreakerSelectionStage,
    FinalValidationStage,
)


class ElectricalEngineRunner:
    """
    Ejecutor principal del motor de cálculos eléctricos.
    Orquesta secuencialmente las etapas del pipeline garantizando inmutabilidad.
    """

    @staticmethod
    def calculate_circuit(inp: CircuitInput) -> CircuitResult:
        # 1. Crear el contexto inicial
        ctx = CalculationContext(input_data=inp)

        # 2. Definir la secuencia exacta de etapas
        stages = [
            NormalizationStage(),
            CurrentCalculationStage(),
            CorrectionFactorsStage(),
            ConductorSelectionStage(),
            VoltageDropStage(),
            IterativeResizeStage(),
            BreakerSelectionStage(),
            FinalValidationStage()
        ]

        # 3. Ejecutar secuencialmente cada etapa
        for stage in stages:
            ctx = stage.execute(ctx)

        # 4. Construir y retornar el resultado consolidado
        return CircuitResult(
            circuit_id=ctx.input_data.circuit_id,
            nominal_current_a=round(ctx.nominal_current_a, 3),
            design_current_a=round(ctx.design_current_a, 3),
            corrected_ampacity_a=round(ctx.selected_conductor.ampacity_corrected_a, 2) if ctx.selected_conductor else 0.0,
            selected_conductor=ctx.selected_conductor,
            selected_breaker=ctx.selected_breaker,
            voltage_drop_percent=round(ctx.voltage_drop_percent, 3),
            is_compliant=ctx.is_compliant,
            alerts=ctx.alerts,
            trace=ctx.trace
        )
