from typing import TYPE_CHECKING
import torch as t
from torch import Tensor
import torch.nn.functional as F
import einops

if TYPE_CHECKING:
    from part31_superposition_and_saes.solutions import Model, SAE


def test_model(Model):
    import part31_superposition_and_saes.solutions as solutions

    cfg = solutions.Config(10, 5, 2)
    # get actual
    model = Model(cfg)
    model_soln = solutions.Model(cfg)
    assert set(model.state_dict().keys()) == set(
        model_soln.state_dict().keys()
    ), "Incorrect parameters."
    model.load_state_dict(model_soln.state_dict())
    batch = model_soln.generate_batch(10)
    out_actual = model(batch)
    out_expected = model_soln(batch)
    assert (
        out_actual.shape == out_expected.shape
    ), f"Expected shape {out_expected.shape}, got {out_actual.shape}"
    assert t.allclose(
        out_actual, F.relu(out_actual)
    ), "Did you forget to apply the ReLU (or do it in the wrong order)?"
    assert t.allclose(out_actual, out_expected), "Incorrect output when compared to solution."
    print("All tests in `test_model` passed!")


def test_generate_batch(Model):
    import part31_superposition_and_saes.solutions as solutions

    n_features = 5
    n_instances = 10
    n_hidden = 2
    batch_size = 5000
    cfg = solutions.Config(n_instances, n_features, n_hidden)
    feature_probability = (t.arange(1, 11) / 11).unsqueeze(-1)
    model = Model(cfg, feature_probability=feature_probability)
    batch = model.generate_batch(batch_size)
    assert batch.shape == (
        batch_size,
        n_instances,
        n_features,
    ), f"Expected shape (500, 10, 5), got {batch.shape}"
    assert t.allclose(
        batch, batch.clamp(0, 1)
    ), "Not all elements of batch are in the [0, 1] range."
    feature_probability = (batch.abs() > 1e-5).float().mean((0, -1))
    diff = (feature_probability - model.feature_probability[:, 0]).abs().sum()
    assert diff < 0.05, "Incorrect feature_probability implementation."
    print("All tests in `test_generate_batch` passed!")


def test_calculate_loss(Model):
    import part31_superposition_and_saes.solutions as solutions

    instances = 10
    features = 5
    d_hidden = 2
    cfg = solutions.Config(instances, features, d_hidden)

    # Define model & solution model, both with trivial importances, and test for equality
    model_soln = solutions.Model(cfg)
    model = Model(cfg)
    batch = model.generate_batch(10)
    out = model(batch)
    expected_loss = model_soln.calculate_loss(out, batch)
    actual_loss = model.calculate_loss(out, batch)
    t.testing.assert_close(expected_loss, actual_loss, msg="Failed test with trivial importances")

    # Now test with nontrivial importances
    importance = t.rand(instances, features)
    model_soln = solutions.Model(cfg, importance=importance)
    model = Model(cfg, importance=importance)
    batch = model.generate_batch(10)
    out = model(batch)
    expected_loss = model_soln.calculate_loss(out, batch)
    actual_loss = model.calculate_loss(out, batch)
    t.testing.assert_close(
        expected_loss, actual_loss, msg="Failed test with nontrivial importances"
    )

    print("All tests in `test_calculate_loss` passed!")


def test_neuron_model(neuron_model):
    import part31_superposition_and_saes.solutions as solutions

    cfg = solutions.Config(
        n_inst=10,
        n_features=5,
        d_hidden=2,
    )

    # Generate model from solutions & from your code
    model_soln = solutions.NeuronModel(cfg)
    model = neuron_model(cfg)
    model.load_state_dict(model_soln.state_dict())

    # Bias is initialized to zero, so we can't tell if it's been added to the forward pass. We will temporarily set it to random values to check if it's being used.
    model.b_final.data = t.randn_like(model.b_final.data)
    model_soln.b_final.data = model.b_final.data.clone()

    # Run forward pass on same data for both models
    batch = model_soln.generate_batch(100)
    out_soln = model_soln(batch)
    try:
        out = model(batch)
    except:
        raise Exception("Error running forward pass on your model")

    # Should get same results
    t.testing.assert_close(out_soln, out)

    print("All tests in `test_neuron_model` passed!")


def test_neuron_computation_model(neuron_computation_model):
    import part31_superposition_and_saes.solutions as solutions

    cfg = solutions.Config(
        n_inst=10,
        n_features=5,
        d_hidden=2,
    )

    # Generate model from solutions & from your code
    model_soln = solutions.NeuronComputationModel(cfg)
    model = neuron_computation_model(cfg)
    model.load_state_dict(model_soln.state_dict())

    # Bias is initialized to zero, so we can't tell if it's been added to the forward pass. We will temporarily set it to random values to check if it's being used.
    model.b_final.data = t.randn_like(model.b_final.data)
    model_soln.b_final.data = model.b_final.data.clone()

    # Run forward pass on same data for both models
    batch = model_soln.generate_batch(100)
    out_soln = model_soln(batch)
    out = model(batch)

    # Should get same results
    t.testing.assert_close(out_soln, out)

    print("All tests in `test_neuron_computation_model` passed!")


def test_compute_dimensionality(compute_dimensionality):
    import part31_superposition_and_saes.solutions as solutions

    W = t.randn(5, 20, 40)
    result = compute_dimensionality(W)
    expected = solutions.compute_dimensionality(W)
    t.testing.assert_close(result, expected)
    print("All tests in `test_compute_dimensionality` passed!")


def setup_sae(
    SAE, match_weights: bool = True, tied: bool = False, bias: bool = False
) -> tuple["SAE", "SAE"]:
    import part31_superposition_and_saes.solutions as solutions

    n_inst = 1
    d_in = d_hidden = 2
    d_sae = n_features = 5

    cfg = solutions.Config(
        n_inst=n_inst,
        n_features=n_features,
        d_hidden=d_hidden,
    )
    sae_cfg = solutions.SAEConfig(
        n_inst=n_inst,
        d_in=d_in,
        d_sae=d_sae,
        tied_weights=tied,
        architecture = "standard",
    )
    model = solutions.Model(cfg)
    sae = SAE(sae_cfg, model)
    soln_sae = solutions.SAE(sae_cfg, model)

    if match_weights:
        if bias:
            sae.b_dec.data = t.randn_like(sae.b_dec.data)
            sae.b_enc.data = t.randn_like(sae.b_enc.data)
            soln_sae.b_dec.data = sae.b_dec.data.clone()
            soln_sae.b_enc.data = sae.b_enc.data.clone()
        sae.load_state_dict(soln_sae.state_dict())

    return sae, soln_sae


def test_sae_init(SAE):
    sae, _ = setup_sae(SAE, tied=False)
    all_params = {"_W_dec", "W_enc", "b_enc", "b_dec", "model.W", "model.b_final"}
    all_params_actual = {name for name, param in sae.named_parameters()}
    invalid_params = all_params_actual - all_params
    missing_params = all_params - all_params_actual
    assert len(invalid_params) == 0, f"Got unexpected parameters: {invalid_params}"
    assert len(missing_params) == 0, f"Missing parameters: {missing_params}"

    assert not sae.model.W.requires_grad
    assert not sae.model.b_final.requires_grad

    sae, _ = setup_sae(SAE, tied=True)
    all_params = {"W_enc", "b_enc", "b_dec", "model.W", "model.b_final"}
    all_params_actual = {name for name, param in sae.named_parameters()}
    invalid_params = all_params_actual - all_params
    missing_params = all_params - all_params_actual
    assert len(invalid_params) == 0, f"Got unexpected parameters: {invalid_params}"
    assert len(missing_params) == 0, f"Missing parameters: {missing_params}"
    print("All tests in `test_sae_init` passed!")


def test_sae_generate_batch(SAE):
    sae, _ = setup_sae(SAE, match_weights=False, tied=False)
    h = sae.generate_batch(100)
    assert h.shape == (100, sae.cfg.n_inst, sae.cfg.d_in), (
        h.shape,
        (100, sae.cfg.n_inst, sae.cfg.d_in),
    )
    print("All tests in `test_sae_generate_batch` passed!")


def test_sae_forward(SAE):
    output_names = ["l1_loss", "l2_loss", "loss", "acts", "h_reconstructed"]

    autoencoder, soln_autoencoder = setup_sae(SAE)
    h = autoencoder.generate_batch(100)
    t.testing.assert_close(
        autoencoder.W_enc,
        soln_autoencoder.W_enc,
        msg="Test failed - please message errata on Slack",
    )

    output = autoencoder.forward(h)
    output_expected = soln_autoencoder.forward(h)
    for name, out, out_expected in zip(output_names, output, output_expected):
        t.testing.assert_close(out, out_expected, msg=f"autoencoder.forward() {name} is incorrect")

    autoencoder, soln_autoencoder = setup_sae(SAE, bias=True)
    h = autoencoder.generate_batch(100)
    t.testing.assert_close(
        autoencoder.W_enc,
        soln_autoencoder.W_enc,
        msg="Test failed - please message errata on Slack",
    )

    output = autoencoder.forward(h)
    output_expected = soln_autoencoder.forward(h)
    for name, out, out_expected in zip(output_names, output, output_expected):
        t.testing.assert_close(
            out,
            out_expected,
            msg=f"autoencoder.forward() {name} is incorrect (did you forget to subtract / add decoder bias?)",
        )

    print("All tests in `test_sae_forward` passed!")


def test_sae_W_dec_normalized(SAE):
    autoencoder = setup_sae(SAE)[1]

    W_dec = autoencoder.W_dec
    W_dec_normalized = autoencoder.W_dec_normalized
    t.testing.assert_close(W_dec / W_dec.norm(dim=-1, keepdim=True), W_dec_normalized)

    # Test dividing by zero
    autoencoder.W_dec.data[:] = 0.0
    W_dec_normalized = autoencoder.W_dec_normalized
    assert W_dec_normalized.pow(2).sum() < 1e-6, f"Failed: {W_dec_normalized}"

    print("All tests in `test_sae_normalize_W_dec` passed!")


@t.no_grad()
def test_resample_simple(SAE):
    window = 5

    import part31_superposition_and_saes.solutions as solutions

    # Create autoencoder, and make sure biases don't start at zero (more robust testing)
    cfg = solutions.Config(
        n_inst=8,
        n_features=5,
        d_hidden=2,
    )
    sae_cfg = solutions.SAEConfig(
        n_inst=8,
        d_in=2,
        d_sae=5,
        l1_coeff=0.25,
    )
    model = solutions.Model(cfg)
    sae = solutions.SAE(sae_cfg, model)
    sae.b_enc.data = t.randn_like(sae.b_enc.data)

    # Get the weights (we rearrange W_enc to be the same shape as W_dec, for easier testing)
    old_W_dec = sae.W_dec.detach().clone()
    old_W_enc = sae.W_enc.detach().clone().transpose(-1, -2)
    old_b_enc = sae.b_enc.detach().clone()

    # Crete 'fract_active_in_window' which is zero at all timesteps with prob 0.5
    frac_active_in_window = t.rand((window, sae_cfg.n_inst, sae_cfg.d_sae))
    features_are_dead = frac_active_in_window[0] < 0.5
    frac_active_in_window[:, features_are_dead] = 0.0

    # Resample latents, and get new weight values (check we have correct return type)
    SAE.resample_simple(sae, frac_active_in_window, 0.5)
    new_W_dec = sae.W_dec.detach().clone()
    new_W_enc = sae.W_enc.detach().clone().transpose(-1, -2)
    new_b_enc = sae.b_enc.detach().clone()

    # Check that b_enc match where the latents aren't dead, and b_enc is zero where they are
    assert (new_b_enc[features_are_dead].abs() < 1e-8).all()
    t.testing.assert_close(new_b_enc[~features_are_dead], old_b_enc[~features_are_dead])

    # Check that W_dec is correct:
    # (1) They should match where the latents aren't dead
    # (2) They should generally not match where the latents are dead (I've tested with >0.5 not ==1 to be on the safe side)
    # (3) Resampled neuron weights should be scaled
    t.testing.assert_close(
        new_W_dec[~features_are_dead],
        old_W_dec[~features_are_dead],
        msg="W_dec weights incorrectly changed where latents are alive",
    )
    assert (
        (new_W_dec[features_are_dead] - old_W_dec[features_are_dead]).abs() > 1e-6
    ).float().mean() > 0.5, "W_dec weights not changed where latents are dead"
    t.testing.assert_close(
        new_W_dec[features_are_dead].norm(dim=-1),
        t.ones_like(new_W_dec[features_are_dead].norm(dim=-1)),
        msg="W_dec failed normalization test",
    )

    # Same checks for W_enc, but we can replace (2) and (3) with checking new features match new W_dec features
    t.testing.assert_close(
        new_W_enc[~features_are_dead],
        old_W_enc[~features_are_dead],
        msg="W_enc weights incorrectly changed where latents are alive",
    )
    t.testing.assert_close(
        new_W_dec[features_are_dead],
        new_W_enc[features_are_dead] / new_W_enc[features_are_dead].norm(dim=-1, keepdim=True),
        msg="Resampled normalized W_enc weights don't match resampled W_dec weights",
    )

    # Finally, do this again when there are no dead latents, and check it doesn't break
    frac_active_in_window = t.ones((window, sae_cfg.n_inst, sae_cfg.d_sae))
    try:
        SAE.resample_simple(sae, frac_active_in_window, 1.0)
    except:
        raise Exception(
            "Error running resample_simple when no latents are dead. Have you dealt with this case correctly?"
        )

    print("All tests in `test_resample_simple` passed!")


@t.no_grad()
def test_resample_advanced(SAE):
    window = 5
    n_instances = 6
    n_hidden = d_in = 10
    n_features = d_sae = 30
    dead_feature_prob = 0.5  # We need at least some alive and some dead, for every instance
    batch_size = 100

    import part31_superposition_and_saes.solutions as solutions

    # Create autoencoder, and make sure biases don't start at zero (more robust testing)
    cfg = solutions.Config(n_instances, n_features, n_hidden)
    sae_cfg = solutions.SAEConfig(n_instances, d_in, d_sae, l1_coeff=0.25)
    model = solutions.Model(cfg)
    sae: "SAE" = SAE(sae_cfg, model)
    sae.b_enc.data = t.randn_like(sae.b_enc.data)
    sae.b_dec.data = t.randn_like(sae.b_dec.data)

    # Get the weights (we rearrange W_enc to be the same shape as W_dec, for easier testing)
    old_W_dec = sae.W_dec.detach().clone()
    old_W_enc = sae.W_enc.detach().clone().transpose(-1, -2)
    old_b_enc = sae.b_enc.detach().clone()

    # Crete 'fract_active_in_window' which is zero at all timesteps with prob 0.5
    frac_active_in_window = t.rand((window, sae_cfg.n_inst, sae_cfg.d_sae))
    features_are_dead = frac_active_in_window[0] < dead_feature_prob
    frac_active_in_window[:, features_are_dead] = 0.0

    # Get the instance indices of dead neurons (useful later)
    dead_instances = t.where(features_are_dead)[0]

    # Get h, and neuron_resample_scale
    h = sae.generate_batch(batch_size=batch_size)
    neuron_resample_scale = 0.4

    # Resample neurons, and get new weight values (check we have correct return type)
    sae.resample_advanced(frac_active_in_window, neuron_resample_scale, batch_size)
    new_W_dec = sae.W_dec.detach().clone()
    new_W_enc = sae.W_enc.detach().clone().transpose(-1, -2)
    new_b_enc = sae.b_enc.detach().clone()

    # Check that b_enc match where the neurons aren't dead, and b_enc is zero where they are
    assert (
        new_b_enc[features_are_dead].abs() < 1e-8
    ).all(), "b_enc not zero where neurons are dead"
    t.testing.assert_close(
        new_b_enc[~features_are_dead],
        old_b_enc[~features_are_dead],
        msg="b_enc weights incorrectly changed where neurons are alive",
    )
    print("Passed basic tests for altering values of encoder bias.")

    # Check that W_dec is correct:
    # (1) They should match where the neurons aren't dead
    # (2) They should generally not match where the neurons are dead (I've tested with >0 not ==1 to be on the safe side)
    # (3) Resampled neuron weights should be normalized
    t.testing.assert_close(
        new_W_dec[~features_are_dead],
        old_W_dec[~features_are_dead],
        msg="W_dec weights incorrectly changed where neurons are alive",
    )
    assert (
        (new_W_dec[features_are_dead] - old_W_dec[features_are_dead]).abs() > 1e-6
    ).float().mean() > 0.0, "W_dec weights not changed where neurons are dead"
    t.testing.assert_close(
        new_W_dec[features_are_dead].norm(dim=-1),
        t.ones_like(new_W_dec[features_are_dead].norm(dim=-1)),
        msg="W_dec failed normalization test",
    )
    print("Passed basic tests for altering values of decoder weight.")

    # Check that W_enc is correct:
    # (1) They should match where the neurons aren't dead
    # (2) Where the neurons are dead, they should match W_dec * neuron_resample_scale * avg_norm(W_enc_alive)
    t.testing.assert_close(
        new_W_enc[~features_are_dead],
        old_W_enc[~features_are_dead],
        msg="W_enc weights incorrectly changed where neurons are alive",
    )
    W_enc_alive_avg_norms = t.tensor(
        [sae.W_enc[i, :, ~features_are_dead[i]].norm(dim=0).mean().item() for i in dead_instances]
    ).to(h.device)

    t.testing.assert_close(
        neuron_resample_scale * W_enc_alive_avg_norms[:, None] * new_W_dec[features_are_dead],
        new_W_enc[features_are_dead],
        msg="Resampled & normalized W_enc weights don't match resampled W_dec weights",
    )
    print("Passed basic tests for altering values of encoder weight.")

    # Next, do this again when there are no dead neurons, and check it doesn't break
    frac_active_in_window_ones = t.ones((window, sae_cfg.n_inst, sae_cfg.d_sae))
    try:
        sae.resample_advanced(frac_active_in_window_ones, neuron_resample_scale, batch_size)
    except:
        raise Exception(
            "Error running resample_advanced when no neurons are dead. Have you dealt with this case correctly?"
        )

    # ! Finally, test the distribution. We do this by making the i-th batch element in the i-th instance
    # ! h[i, i, :] very large, and check if it gets sampled most of the time
    # Get a fixed `h` vector, and change our `generate_batch` function so it'll return this
    t.random.manual_seed(0)
    h = t.randn(batch_size, sae_cfg.n_inst, sae_cfg.d_in).to(h.device) * 0.1
    h[range(n_instances), range(n_instances), :] += 20
    sae.generate_batch = lambda batch_size: h
    # Resample from the SAE, and get the new decoder weights
    sae.resample_advanced(frac_active_in_window, neuron_resample_scale, batch_size)
    resampled_data = sae.W_dec[features_are_dead]  # [n_dead, d_in]
    # Get the h vectors which we know should have been used in the resampling (because they're big)
    h_large = h[range(n_instances), range(n_instances), :]  # [n_dead, d_in]
    h_to_replace = h_large[dead_instances]
    h_to_replace_cent = h_to_replace - sae.b_dec[dead_instances]
    # Get the expected replacement values (one where you forget to center h)
    resampled_data_expected = h_to_replace_cent / h_to_replace_cent.norm(dim=-1, keepdim=True)
    resampled_data_expected_uncentered = h_to_replace / h_to_replace.norm(dim=-1, keepdim=True)
    # Get the error, and figure out what case we're in: correct, forgot to normalize, or different error
    error_from_correct_answer = (resampled_data - resampled_data_expected).abs().mean().item()
    error_from_unnormalized_answer = (
        (resampled_data - resampled_data_expected_uncentered).abs().mean().item()
    )

    if error_from_correct_answer == 0:
        print("Passed distribution tests, to see if resampling was proportional to L2.")
        print("All tests in `test_resample_simple` passed!")
    elif error_from_unnormalized_answer == 0:
        raise Exception(
            "Based on this error, you might have forgotten to subtract 'sae.b_dec' from 'h' before indexing into it to get resampling data."
        )
    else:
        raise Exception(
            "Not correctly using the squared L2 loss as probabilities to resample neurons with replacement."
        )
