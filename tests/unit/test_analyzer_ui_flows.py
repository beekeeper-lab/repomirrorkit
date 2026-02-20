"""Unit tests for the UI flow analyzer."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.ui_flows import analyze_ui_flows
from repo_mirror_kit.harvester.analyzers.surfaces import UIFlowSurface
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inventory(files: list[FileEntry]) -> InventoryResult:
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=sum(f.size for f in files),
        total_skipped=0,
    )


def _make_profile() -> StackProfile:
    return StackProfile(stacks={}, evidence={}, signals=[])


def _write_file(tmp_path: Path, rel_path: str, content: str) -> FileEntry:
    full_path = tmp_path / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    ext = ""
    dot = rel_path.rfind(".")
    if dot != -1:
        ext = rel_path[dot:]
    return FileEntry(
        path=rel_path, size=len(content), extension=ext, hash="abc123", category="source"
    )


# ---------------------------------------------------------------------------
# Empty / no matches
# ---------------------------------------------------------------------------


class TestEmptyResults:
    """Verify analyzer returns empty list when no UI flow patterns are present."""

    def test_no_flow_patterns(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/utils.ts",
            "export function add(a: number, b: number) { return a + b; }\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        assert result == []

    def test_no_workdir_returns_empty(self) -> None:
        entry = FileEntry(
            path="src/wizard.tsx", size=100, extension=".tsx", hash="abc123", category="source"
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=None)

        assert result == []

    def test_non_source_files_skipped(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "styles/wizard.css",
            ".wizard { display: flex; }\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        assert result == []


# ---------------------------------------------------------------------------
# Wizard / stepper detection
# ---------------------------------------------------------------------------


class TestWizardDetection:
    """Tests for multi-step wizard/stepper component detection."""

    def test_stepper_component_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/components/CheckoutWizard.tsx",
            """\
import React from 'react';

function CheckoutWizard() {
  return (
    <Stepper activeStep={currentStep}>
      <Step label="Shipping">
        <ShippingForm />
      </Step>
      <Step label="Payment">
        <PaymentForm />
      </Step>
      <Step label="Review">
        <ReviewOrder />
      </Step>
    </Stepper>
  );
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        wizard_surfaces = [s for s in result if s.flow_type == "wizard"]
        assert len(wizard_surfaces) >= 1
        surface = wizard_surfaces[0]
        assert isinstance(surface, UIFlowSurface)
        assert surface.surface_type == "ui_flow"
        assert surface.flow_type == "wizard"
        assert "Shipping" in surface.steps
        assert "Payment" in surface.steps
        assert "Review" in surface.steps
        assert surface.entry_point == "Shipping"
        assert surface.exit_points == ["Review"]

    def test_wizard_component_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/components/SetupFlow.tsx",
            """\
function SetupFlow() {
  return (
    <Wizard>
      <WizardStep label="Account">
        <AccountForm />
      </WizardStep>
      <WizardStep label="Profile">
        <ProfileForm />
      </WizardStep>
    </Wizard>
  );
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        wizard_surfaces = [s for s in result if s.flow_type == "wizard"]
        assert len(wizard_surfaces) >= 1
        surface = wizard_surfaces[0]
        assert "Account" in surface.steps
        assert "Profile" in surface.steps

    def test_steps_array_pattern_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/components/FormWizard.tsx",
            """\
function FormWizard() {
  const activeStep = 0;
  const steps = [
    { label: "Personal Info" },
    { label: "Address" },
    { label: "Confirm" },
  ];
  return <div>wizard content</div>;
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        wizard_surfaces = [s for s in result if s.flow_type == "wizard"]
        assert len(wizard_surfaces) >= 1
        surface = wizard_surfaces[0]
        assert "Personal Info" in surface.steps
        assert "Address" in surface.steps
        assert "Confirm" in surface.steps

    def test_active_step_state_without_wizard_component(self, tmp_path: Path) -> None:
        """activeStep state variable alone indicates a wizard pattern."""
        entry = _write_file(
            tmp_path,
            "src/components/CustomWizard.tsx",
            """\
function CustomWizard() {
  const [activeStep, setActiveStep] = useState(0);
  return <div>{renderStep(activeStep)}</div>;
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        wizard_surfaces = [s for s in result if s.flow_type == "wizard"]
        assert len(wizard_surfaces) >= 1

    def test_wizard_name_from_filename(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/components/RegistrationWizard.tsx",
            """\
function RegistrationWizard() {
  return (
    <Stepper>
      <Step label="Email" />
      <Step label="Password" />
    </Stepper>
  );
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        wizard_surfaces = [s for s in result if s.flow_type == "wizard"]
        assert len(wizard_surfaces) >= 1
        assert wizard_surfaces[0].name == "wizard:RegistrationWizard"

    def test_source_refs_populated(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/Wizard.tsx",
            """\
function MyWizard() {
  return (
    <Stepper>
      <Step label="One" />
    </Stepper>
  );
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        wizard_surfaces = [s for s in result if s.flow_type == "wizard"]
        assert len(wizard_surfaces) >= 1
        surface = wizard_surfaces[0]
        assert len(surface.source_refs) == 1
        assert surface.source_refs[0].file_path == "src/Wizard.tsx"
        assert surface.source_refs[0].start_line is not None
        assert surface.source_refs[0].start_line > 0


# ---------------------------------------------------------------------------
# Navigation guard detection
# ---------------------------------------------------------------------------


class TestNavigationGuardDetection:
    """Tests for router navigation guard detection."""

    def test_vue_before_each_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/router/index.ts",
            """\
import { createRouter } from 'vue-router';

const router = createRouter({ routes });

router.beforeEach((to, from, next) => {
  if (!isAuthenticated()) {
    next('/login');
  }
  next();
});
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        nav_surfaces = [s for s in result if s.flow_type == "navigation"]
        assert len(nav_surfaces) >= 1
        guard_names = [s.entry_point for s in nav_surfaces]
        assert "beforeEach" in guard_names

    def test_vue_before_route_enter_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/views/Dashboard.ts",
            """\
export default {
  beforeRouteEnter(to, from, next) {
    next();
  },
};
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        nav_surfaces = [s for s in result if s.flow_type == "navigation"]
        assert len(nav_surfaces) >= 1
        entry_points = [s.entry_point for s in nav_surfaces]
        assert "beforeRouteEnter" in entry_points

    def test_angular_guard_class_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/guards/auth.guard.ts",
            """\
import { Injectable } from '@angular/core';

@Injectable()
class AuthGuard implements CanActivate {
  canActivate(route, state) {
    return this.authService.isLoggedIn();
  }
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        nav_surfaces = [s for s in result if s.flow_type == "navigation"]
        assert len(nav_surfaces) >= 1
        guard_surface = [s for s in nav_surfaces if "AuthGuard" in s.name]
        assert len(guard_surface) >= 1
        assert guard_surface[0].entry_point == "AuthGuard"

    def test_angular_can_deactivate_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/guards/unsaved.guard.ts",
            """\
class UnsavedGuard implements CanDeactivate {
  canDeactivate(component) {
    return component.canLeave();
  }
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        nav_surfaces = [s for s in result if s.flow_type == "navigation"]
        assert len(nav_surfaces) >= 1

    def test_navigation_guard_steps_field(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/router/guards.ts",
            """\
router.beforeEach((to, from, next) => {
  next();
});
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        nav_surfaces = [s for s in result if s.flow_type == "navigation"]
        assert len(nav_surfaces) >= 1
        assert nav_surfaces[0].steps == ["beforeEach"]

    def test_navigation_event_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/hooks/navigation.ts",
            """\
const onBeforeNavigate = (callback) => {
  window.addEventListener('beforeunload', callback);
};
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        nav_surfaces = [s for s in result if s.flow_type == "navigation"]
        assert len(nav_surfaces) >= 1
        entry_points = [s.entry_point for s in nav_surfaces]
        assert "onBeforeNavigate" in entry_points


# ---------------------------------------------------------------------------
# Modal chain detection
# ---------------------------------------------------------------------------


class TestModalChainDetection:
    """Tests for modal/dialog chain pattern detection."""

    def test_multiple_named_modals_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/components/ConfirmFlow.tsx",
            """\
function ConfirmFlow() {
  return (
    <div>
      <Dialog title="Select Item" open={showSelect}>
        <ItemList />
      </Dialog>
      <Dialog title="Confirm Selection" open={showConfirm}>
        <ConfirmDetails />
      </Dialog>
      <Dialog title="Success" open={showSuccess}>
        <SuccessMessage />
      </Dialog>
    </div>
  );
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        modal_surfaces = [s for s in result if s.flow_type == "modal_chain"]
        assert len(modal_surfaces) >= 1
        surface = modal_surfaces[0]
        assert "Select Item" in surface.steps
        assert "Confirm Selection" in surface.steps
        assert "Success" in surface.steps
        assert surface.entry_point == "Select Item"
        assert surface.exit_points == ["Success"]

    def test_single_modal_not_detected_as_chain(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/components/SimpleDialog.tsx",
            """\
function SimpleDialog() {
  return (
    <Dialog title="Confirm" open={isOpen}>
      <p>Are you sure?</p>
    </Dialog>
  );
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        modal_surfaces = [s for s in result if s.flow_type == "modal_chain"]
        assert modal_surfaces == []

    def test_multiple_modal_states_with_component(self, tmp_path: Path) -> None:
        """Multiple modal state toggles with a Modal component indicate a chain."""
        entry = _write_file(
            tmp_path,
            "src/components/ComplexModal.tsx",
            """\
function ComplexModal() {
  const showModal = false;
  const openModal = () => {};
  const closeModal = () => {};
  const isModalOpen = false;
  return <Modal open={isModalOpen}>content</Modal>;
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        modal_surfaces = [s for s in result if s.flow_type == "modal_chain"]
        assert len(modal_surfaces) >= 1


# ---------------------------------------------------------------------------
# Onboarding flow detection
# ---------------------------------------------------------------------------


class TestOnboardingDetection:
    """Tests for onboarding/welcome flow detection."""

    def test_onboarding_path_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/pages/onboarding/index.tsx",
            """\
function OnboardingPage() {
  return <div>Welcome to our app!</div>;
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        # File path contains "onboarding", so it should be detected.
        onboarding_surfaces = [s for s in result if s.flow_type == "form_sequence"]
        assert len(onboarding_surfaces) >= 1

    def test_onboarding_component_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/components/Setup.tsx",
            """\
function Setup() {
  return (
    <OnboardingWizard>
      <OnboardingStep title="Welcome">
        <WelcomeContent />
      </OnboardingStep>
      <OnboardingStep title="Profile Setup">
        <ProfileForm />
      </OnboardingStep>
    </OnboardingWizard>
  );
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        onboarding_surfaces = [s for s in result if s.flow_type == "form_sequence"]
        assert len(onboarding_surfaces) >= 1
        surface = onboarding_surfaces[0]
        assert "Welcome" in surface.steps
        assert "Profile Setup" in surface.steps

    def test_welcome_path_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/pages/welcome/index.tsx",
            """\
function WelcomePage() {
  return <div>Welcome!</div>;
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        onboarding_surfaces = [s for s in result if s.flow_type == "form_sequence"]
        assert len(onboarding_surfaces) >= 1

    def test_getting_started_path_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/pages/getting-started.tsx",
            """\
function GettingStarted() {
  return <div>Let's get started</div>;
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        onboarding_surfaces = [s for s in result if s.flow_type == "form_sequence"]
        assert len(onboarding_surfaces) >= 1

    def test_onboarding_entry_point_from_steps(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/onboarding/Flow.tsx",
            """\
function Flow() {
  return (
    <div>
      <OnboardingStep title="Step One">content</OnboardingStep>
      <OnboardingStep title="Step Two">content</OnboardingStep>
    </div>
  );
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        onboarding_surfaces = [s for s in result if s.flow_type == "form_sequence"]
        assert len(onboarding_surfaces) >= 1
        surface = onboarding_surfaces[0]
        assert surface.entry_point == "Step One"
        assert surface.exit_points == ["Step Two"]

    def test_tour_component_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/components/AppTour.tsx",
            """\
function AppTour() {
  return (
    <Walkthrough>
      <TourStep title="Feature A">Explanation A</TourStep>
      <TourStep title="Feature B">Explanation B</TourStep>
    </Walkthrough>
  );
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        onboarding_surfaces = [s for s in result if s.flow_type == "form_sequence"]
        assert len(onboarding_surfaces) >= 1
        surface = onboarding_surfaces[0]
        assert "Feature A" in surface.steps
        assert "Feature B" in surface.steps


# ---------------------------------------------------------------------------
# Surface type and source refs
# ---------------------------------------------------------------------------


class TestSurfaceTypeAndRefs:
    """Verify surface_type and source_refs across all flow types."""

    def test_all_surfaces_are_ui_flow_type(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/Wizard.tsx",
            """\
function Wizard() {
  return (
    <Stepper>
      <Step label="A" />
      <Step label="B" />
    </Stepper>
  );
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        for surface in result:
            assert isinstance(surface, UIFlowSurface)
            assert surface.surface_type == "ui_flow"

    def test_source_refs_have_file_path(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/router/guards.ts",
            """\
router.beforeEach((to, from, next) => { next(); });
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        for surface in result:
            assert len(surface.source_refs) >= 1
            assert surface.source_refs[0].file_path == "src/router/guards.ts"
            assert surface.source_refs[0].start_line is not None


# ---------------------------------------------------------------------------
# Multiple flow types
# ---------------------------------------------------------------------------


class TestMultipleFlowTypes:
    """Tests for repositories with multiple UI flow types."""

    def test_wizard_and_nav_guard_in_same_repo(self, tmp_path: Path) -> None:
        entry1 = _write_file(
            tmp_path,
            "src/components/Checkout.tsx",
            """\
function Checkout() {
  return (
    <Stepper>
      <Step label="Cart" />
      <Step label="Pay" />
    </Stepper>
  );
}
""",
        )
        entry2 = _write_file(
            tmp_path,
            "src/router/guards.ts",
            """\
router.beforeEach((to, from, next) => { next(); });
""",
        )
        inventory = _make_inventory([entry1, entry2])
        result = analyze_ui_flows(inventory, _make_profile(), workdir=tmp_path)

        flow_types = {s.flow_type for s in result}
        assert "wizard" in flow_types
        assert "navigation" in flow_types
