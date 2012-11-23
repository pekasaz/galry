import numpy as np
import os
from visual import Visual
from fontmaps import load_font
from ..debugtools import log_debug, log_info, log_warn

class TextVisual(Visual):
    """Template for displaying short text on a single line.
    
    It uses the following technique: each character is rendered as a sprite,
    i.e. a pixel with a large point size, and a single texture for every point.
    The texture contains a font atlas, i.e. all characters in a given font.
    Every point comes with coordinates that indicate which small portion
    of the font atlas to display (that portion corresponds to the character).
    This is all done automatically, thanks to a font atlas stored in the
    `fontmaps` folder. There needs to be one font atlas per font and per font
    size. Also, there is a configuration text file with the coordinates and
    size of every character. The software used to generate font maps is
    AngelCode Bitmap Font Generator.
    
    For now, there is only the Segoe font.
    
    """
    
    def position_compound(self, position=None):
        """Compound variable with the position of the text. All characters
        are at the exact same position, and are then shifted in the vertex
        shader."""
        if position is None:
            position = (0., 0.)
        position = np.tile(np.array(position).reshape((1, -1)), self.size)
        return dict(position=position)
    
    def text_compound(self, text):
        """Compound variable for the text string. It changes the text map,
        the character position, and the text width."""
        text_map = self.get_map(text)
        offset = np.hstack((0., np.cumsum(text_map[:, 2])[:-1]))    
        text_map = self.get_map(text.ljust(self.size, ' '))
        return dict(text_map=text_map, offset=offset, text_width=offset[-1])
    
    def initialize_font(self, font, fontsize):
        """Initialize the specified font at a given size."""
        self.texture, self.matrix, self.get_map = load_font(font, fontsize)

    def initialize(self, text, pos=(0., 0.), font='segoe', fontsize=24, color=None):
        """Initialize the text template."""
        
        if color is None:
            color = self.default_color
        
        self.size = len(text)
        self.primitive_type = 'POINTS'

        text_length = self.size
        self.initialize_font(font, fontsize)
        
        point_size = float(self.matrix[:,4].max() * self.texture.shape[1])

        # template attributes and varyings
        self.add_attribute("position", vartype="float", ndim=2, data=np.zeros((self.size, 2)))
            
        self.add_attribute("offset", vartype="float", ndim=1)
        self.add_attribute("text_map", vartype="float", ndim=4)
        self.add_varying("flat_text_map", vartype="float", flat=True, ndim=4)
        
        # texture
        self.add_texture("tex_sampler", size=self.texture.shape[:2], ndim=2,
                            ncomponents=self.texture.shape[2],
                            data=self.texture)
        
        # pure heuristic
        letter_spacing = (100 + 17. * fontsize)
        self.add_uniform("letter_spacing", vartype="float", ndim=1,
                            data=letter_spacing)
        self.add_uniform("point_size", vartype="float", ndim=1,
                            data=point_size)
        self.add_uniform("color", vartype="float", ndim=4, data=color)
        self.add_uniform("text_width", vartype="float", ndim=1)
        
        # compound variables
        self.add_compound("text", fun=self.text_compound, data=text)
        self.add_compound("pos", fun=self.position_compound, data=pos)

        # vertex shader
        self.add_vertex_main("""
    gl_Position.x += (offset - text_width / 2) * letter_spacing / window_size.x;
    gl_PointSize = point_size;
    flat_text_map = text_map;
        """, 'end')

        # fragment shader
        fragment = """
    // relative coordinates of the pixel within the sprite (in [0,1])
    float x = gl_PointCoord.x;
    float y = gl_PointCoord.y;
    
    // size of the corresponding character
    float w = flat_text_map.z;
    float h = flat_text_map.w;
    
    // display the character at the left of the sprite
    float delta = h / w;
    x = delta * x;
    if ((x >= 0) && (x <= 1))
    {
        // coordinates of the character in the font atlas
        vec2 coord = flat_text_map.xy + vec2(w * x, h * y);
        out_color = texture(tex_sampler, coord) * color;
    }
    else
        out_color = vec4(0, 0, 0, 0);
        """
        
        self.add_fragment_main(fragment)
        
        