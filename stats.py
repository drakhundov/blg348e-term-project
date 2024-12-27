import vcf
from collections import defaultdict


def extract_variants(vcf_file):
    variants = set()
    vcf_reader = vcf.Reader(open(vcf_file, "r"))
    for record in vcf_reader:
        variants.add((record.CHROM, record.POS, record.REF, str(record.ALT[0])))
    return variants


def calculate_f1_score(predicted_vcf, reference_vcf):
    predicted_variants = extract_variants(predicted_vcf)
    reference_variants = extract_variants(reference_vcf)

    tp = len(predicted_variants & reference_variants)
    fp = len(predicted_variants - reference_variants)
    fn = len(reference_variants - predicted_variants)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )

    return precision, recall, f1_score


# Example usage
predicted_vcf = "variants/bwa_somaticsniper_recal.vcf"
reference_vcf = "performance/_bwa_somaticsniper_recal.vcf.recode.vcf"

precision, recall, f1_score = calculate_f1_score(predicted_vcf, reference_vcf)
print(f"Precision: {precision}")
print(f"Recall: {recall}")
print(f"F1 Score: {f1_score}")
