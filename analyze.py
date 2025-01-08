from cyvcf2 import VCF


def evaluate_vcf(vcf_reference_file, vcf_sample_file):
    vcf_reference = VCF(vcf_reference_file)
    vcf_sample = VCF(vcf_sample_file)

    variants_ref = [
        (variant.CHROM, variant.POS, variant.REF, variant.ALT)
        for variant in vcf_reference
    ]
    variants_sample = [
        (variant.CHROM, variant.POS, variant.REF, variant.ALT) for variant in vcf_sample
    ]

    false_positive = 0  # only in sample
    true_positive = 0  # matching
    false_negative = 0  # only in reference
    true_negative = 0  # not in reference and not in sample

    for variant in variants_sample:
        if variant not in variants_ref:
            false_positive += 1
        else:
            true_positive += 1

    for variant in variants_ref:
        if variant not in variants_sample:
            false_negative += 1

    precision = (
        true_positive / (true_positive + false_positive)
        if (true_positive + false_positive) > 0
        else 0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if (true_positive + false_negative) > 0
        else 0
    )
    f1_score = (
        2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    )
    accuracy = (
        (true_positive + true_negative)
        / (true_positive + true_negative + false_positive + false_negative)
        if (true_positive + true_negative + false_positive + false_negative) > 0
        else 0
    )

    return precision, recall, f1_score, accuracy


evaluate_vcf("hc_bed_filtered.recode.vcf", "variants/bwa_somaticsniper_recal.vcf")
