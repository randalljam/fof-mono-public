import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;

/**
 * Standalone utility to generate the Wandering Nerd 64x64 PNG texture.
 *
 * Usage: java GenerateNerdTexture [input_villager.png] [output_nerd.png]
 *
 * Defaults:
 *   input:  tools/villager_base.png
 *   output: src/main/resources/assets/mathquest/textures/entity/wandering_nerd.png
 *
 * Also writes a 16x scaled preview to tools/wandering_nerd_preview.png
 * so you can see the texture without squinting at 64x64.
 */
public class GenerateNerdTexture {

    public static void main(String[] args) throws Exception {
        String inputPath = args.length > 0 ? args[0] : "tools/villager_base.png";
        String outputPath = args.length > 1 ? args[1]
            : "src/main/resources/assets/mathquest/textures/entity/wandering_nerd.png";

        File inputFile = new File(inputPath);
        String previewPath = inputFile.getParent() != null
            ? inputFile.getParent() + "/wandering_nerd_preview.png"
            : "wandering_nerd_preview.png";

        System.out.println("Input:   " + inputPath);
        System.out.println("Output:  " + outputPath);
        System.out.println("Preview: " + previewPath);

        BufferedImage image = ImageIO.read(new File(inputPath));
        if (image.getWidth() != 64 || image.getHeight() != 64) {
            System.err.println("ERROR: Expected 64x64, got " + image.getWidth() + "x" + image.getHeight());
            System.exit(1);
        }

        clearHatOverlay(image);
        drawGlasses(image);

        File outputFile = new File(outputPath);
        outputFile.getParentFile().mkdirs();
        ImageIO.write(image, "png", outputFile);
        System.out.println("Wrote texture: " + outputPath);

        // Write a scaled-up preview (16x) for easy visual inspection
        int scale = 16;
        BufferedImage preview = new BufferedImage(64 * scale, 64 * scale, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = preview.createGraphics();
        g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_NEAREST_NEIGHBOR);
        g.drawImage(image, 0, 0, 64 * scale, 64 * scale, null);

        // Draw grid lines and UV labels on the preview
        g.setColor(new Color(255, 255, 255, 40));
        for (int i = 0; i <= 64; i++) {
            g.drawLine(i * scale, 0, i * scale, 64 * scale);
            g.drawLine(0, i * scale, 64 * scale, i * scale);
        }
        g.setColor(new Color(255, 255, 0, 120));
        g.setFont(new Font("Monospaced", Font.PLAIN, 10));
        g.drawString("Head front: u=8..16, v=8..18", 8 * scale, 7 * scale);
        g.drawString("Hat overlay: u=32..64, v=0..18 (cleared)", 32 * scale, 20 * scale);
        g.drawString("L side: u=0..8", 0, 7 * scale);
        g.drawString("R side: u=16..24", 16 * scale, 7 * scale);
        g.dispose();

        ImageIO.write(preview, "png", new File(previewPath));
        System.out.println("Wrote preview: " + previewPath);
    }

    static void clearHatOverlay(BufferedImage image) {
        // Hat overlay occupies u=32..64, v=0..18 on the 64x64 texture.
        // Clear it all to transparent so the inner head (with glasses) shows.
        int transparent = 0x00000000;
        for (int x = 32; x < 64; x++) {
            for (int y = 0; y < 18; y++) {
                image.setRGB(x, y, transparent);
            }
        }
    }

    static void drawGlasses(BufferedImage image) {
        // Standard ARGB: 0xAARRGGBB
        int black     = 0xFF000000;
        int lensCyan  = 0xFFB0DCE8;   // Slight blue lens tint
        int eyeWhite  = 0xFFFFFFFF;   // Eye sclera
        int eyeGreen  = 0xFF2D8A2D;   // Eye iris
        int tapeWhite = 0xFFE8D8C8;   // Off-white tape
        int tapeGray  = 0xFFB8A898;   // Tape edge

        // ---- Head front face: u=8..16, v=8..18 ----
        // Vanilla villager eyes are at v=13. Glasses frame the eyes.
        //
        //   u:  8   9  10  11  12  13  14  15
        //  v=12: F   F   F   F   T   F   F   F    <- top frame
        //  v=13: F   W   G   F   T   F   G   W    <- eye row (W=white, G=green)
        //  v=14: F   F   F   F   T   F   F   F    <- bottom frame

        // Left lens frame (u=8..12, v=12..15) - 4 wide, 3 tall
        fillRect(image, 8, 12, 12, 15, black);
        // Left lens interior: cyan tint then eye pixels
        image.setRGB(9, 13, lensCyan);
        image.setRGB(10, 13, lensCyan);
        image.setRGB(9, 13, eyeWhite);
        image.setRGB(10, 13, eyeGreen);

        // Right lens frame (u=12..16, v=12..15) - 4 wide, 3 tall
        fillRect(image, 12, 12, 16, 15, black);
        // Right lens interior: cyan tint then eye pixels
        image.setRGB(13, 13, lensCyan);
        image.setRGB(14, 13, lensCyan);
        image.setRGB(13, 13, eyeGreen);
        image.setRGB(14, 13, eyeWhite);

        // Tape on bridge (u=11..13, v=12..15) over the black frames
        fillRect(image, 11, 12, 13, 15, tapeWhite);
        // Tape edge pixels above and below
        image.setRGB(11, 11, tapeGray);
        image.setRGB(12, 11, tapeGray);
        image.setRGB(11, 15, tapeGray);
        image.setRGB(12, 15, tapeGray);

        // ---- Temple arms on side faces ----
        // Left side face: u=0..8, v=8..18
        fillRect(image, 5, 13, 8, 14, black);

        // Right side face: u=16..24, v=8..18
        fillRect(image, 16, 13, 19, 14, black);
    }

    static void fillRect(BufferedImage image, int x1, int y1, int x2, int y2, int color) {
        for (int x = x1; x < x2; x++) {
            for (int y = y1; y < y2; y++) {
                if (x >= 0 && x < image.getWidth() && y >= 0 && y < image.getHeight()) {
                    image.setRGB(x, y, color);
                }
            }
        }
    }
}
